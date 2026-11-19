"""
Formularios de la app ``web`` (login, crear cuenta y recuperación de cuenta).

Se extienden los formularios de Django para agregar clases CSS y
atributos de accesibilidad: la validación es la oficial de Django.
"""
import logging

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template import loader

from usuarios.models import CARRERAS_UNEMI

from .activacion import ERRORES_CORREO, enviar_correo_activacion, ocultar_correo, puede_reenviar

logger = logging.getLogger(__name__)

CLASE_CAMPO = "campo__entrada"


def _estilizar(campos, atributos_por_campo):
    """Agrega la clase CSS y atributos extra a cada widget."""
    for nombre, campo in campos.items():
        campo.widget.attrs.update({"class": CLASE_CAMPO, **atributos_por_campo.get(nombre, {})})


class FormularioLogin(AuthenticationForm):
    """
    Inicio de sesión con usuario y contraseña.

    Si la cuenta se creó en /registro/ y todavía no se activó, en vez de
    «usuario o contraseña incorrectos» se explica qué pasa y se reenvía el
    enlace de activación (como máximo uno cada 5 minutos).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        _estilizar(
            self.fields,
            {
                "username": {"autocomplete": "username", "autofocus": True},
                "password": {"autocomplete": "current-password"},
            },
        )

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            usuario = self._cuenta_sin_activar()
            if usuario is None:
                raise
            raise forms.ValidationError(self._avisar_activacion(usuario), code="inactive")

    def _cuenta_sin_activar(self):
        """La cuenta de /registro/ sin activar, solo si la contraseña es correcta."""
        nombre = self.cleaned_data.get("username")
        clave = self.cleaned_data.get("password")
        if not nombre or not clave:
            return None
        usuario = get_user_model().objects.filter(
            username=nombre, is_active=False, correo_pendiente=True
        ).first()
        if usuario and usuario.email and usuario.check_password(clave):
            return usuario
        return None

    def _avisar_activacion(self, usuario):
        correo = ocultar_correo(usuario.email)
        if not puede_reenviar(usuario):
            return (f"Tu cuenta aún no está activada. Abre el enlace que enviamos a {correo} "
                    "(revisa también spam). Si no llegó, intenta de nuevo en unos minutos.")
        try:
            enviar_correo_activacion(self.request, usuario)
        except ERRORES_CORREO:
            logger.exception("No se pudo reenviar el correo de activación")
            return ("Tu cuenta aún no está activada y no pudimos enviarte el enlace en este "
                    "momento. Intenta más tarde o avisa al administrador.")
        return (f"Tu cuenta aún no está activada. Te enviamos un enlace nuevo a {correo}: "
                "ábrelo y vuelve a ingresar. Revisa también la carpeta de spam.")


class FormularioRegistro(UserCreationForm):
    """
    Crear cuenta desde la página. Todos los datos son obligatorios porque el
    correo sirve para activar y recuperar la cuenta, y la carrera para el
    ranking. La cuenta nace inactiva (ver web/activacion.py).
    """

    semestre = forms.TypedChoiceField(
        label="Semestre",
        coerce=int,
        choices=[("", "Elige tu semestre")] + [(n, f"{n}.º semestre") for n in range(1, 11)],
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("first_name", "last_name", "email", "username", "carrera", "semestre")
        labels = {
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "username": "Usuario",
            "carrera": "Carrera",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre in ("first_name", "last_name", "email", "carrera"):
            self.fields[nombre].required = True
        self.fields["carrera"].choices = [("", "Elige tu carrera")] + CARRERAS_UNEMI
        self.fields["username"].help_text = "Con este nombre vas a ingresar. Sin espacios."
        self.fields["email"].help_text = "Te enviaremos un enlace para activar la cuenta."
        self.fields["password1"].label = "Contraseña"
        self.fields["password1"].help_text = "Mínimo 8 caracteres, que no sean solo números."
        self.fields["password2"].label = "Repite la contraseña"
        self.fields["password2"].help_text = ""
        _estilizar(
            self.fields,
            {
                "first_name": {"autocomplete": "given-name", "autofocus": True},
                "last_name": {"autocomplete": "family-name"},
                "email": {"autocomplete": "email", "inputmode": "email"},
                "username": {"autocomplete": "username", "autocapitalize": "none"},
                "password1": {"autocomplete": "new-password"},
                "password2": {"autocomplete": "new-password"},
            },
        )

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        dominio = correo.rpartition("@")[2]
        if settings.REGISTRO_DOMINIOS and dominio not in settings.REGISTRO_DOMINIOS:
            permitidos = ", ".join(f"@{d}" for d in settings.REGISTRO_DOMINIOS)
            raise forms.ValidationError(f"Usa tu correo institucional ({permitidos}).")
        if get_user_model().objects.filter(email__iexact=correo).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta con este correo. Si olvidaste tus datos, usa "
                "«¿Olvidaste tu usuario?» o «¿Olvidaste tu contraseña?» en el inicio de sesión."
            )
        return correo

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.es_estudiante = True
        usuario.is_staff = False
        usuario.is_superuser = False
        usuario.is_active = False  # Se activa con el enlace del correo
        usuario.correo_pendiente = True
        if commit:
            usuario.save()
        return usuario


class FormularioRecuperarClave(PasswordResetForm):
    """Pide el correo para enviar el enlace de nueva contraseña."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Correo electrónico"
        _estilizar(self.fields, {"email": {"autocomplete": "email", "autofocus": True}})

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Igual que el de Django, pero SIN ocultar los errores de envío.

        Django (4.1+) atrapa cualquier error del servidor de correo y solo lo
        escribe en el log, así que la página decía «te enviamos el enlace»
        aunque el correo nunca saliera. Aquí el error sube a la vista
        (RecuperarClaveView), que muestra un mensaje claro.
        """
        asunto = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        cuerpo = loader.render_to_string(email_template_name, context)
        mensaje = EmailMultiAlternatives(asunto, cuerpo, from_email, [to_email])
        if html_email_template_name:
            mensaje.attach_alternative(loader.render_to_string(html_email_template_name, context), "text/html")
        mensaje.send()


class FormularioNuevaClave(SetPasswordForm):
    """Formulario para escribir la nueva contraseña (desde el enlace del correo)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Nueva contraseña"
        self.fields["new_password2"].label = "Repite la nueva contraseña"
        _estilizar(
            self.fields,
            {
                "new_password1": {"autocomplete": "new-password", "autofocus": True},
                "new_password2": {"autocomplete": "new-password"},
            },
        )


class FormularioRecuperarUsuario(forms.Form):
    """Envía por correo el nombre de usuario asociado a un email."""

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={"class": CLASE_CAMPO, "autocomplete": "email", "autofocus": True}
        ),
    )

    def enviar_usuario(self):
        """
        Envía el usuario solo si el correo existe, pero NO lo revela: la
        vista siempre muestra el mismo mensaje (evita adivinar correos).
        """
        email = self.cleaned_data["email"]
        usuarios = get_user_model().objects.filter(email__iexact=email, is_active=True)
        nombres = [usuario.username for usuario in usuarios]
        if not nombres:
            return

        cuerpo = (
            "Hola:\n\n"
            "Recibimos una solicitud para recordar tu nombre de usuario en UNEMI Guide AI.\n\n"
            f"Tu usuario es: {', '.join(nombres)}\n\n"
            "Si no hiciste esta solicitud, puedes ignorar este correo.\n\n"
            "UNEMI Guide AI"
        )
        send_mail(
            subject="UNEMI Guide AI · Tu nombre de usuario",
            message=cuerpo,
            from_email=None,  # Usa DEFAULT_FROM_EMAIL
            recipient_list=[email],
        )

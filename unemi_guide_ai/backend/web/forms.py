"""
Formularios de la app ``web`` (login y recuperación de cuenta).

Se extienden los formularios de Django solo para agregar clases CSS y
atributos de accesibilidad: la validación es la oficial de Django.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.mail import send_mail

CLASE_CAMPO = "campo__entrada"


def _estilizar(campos, atributos_por_campo):
    """Agrega la clase CSS y atributos extra a cada widget."""
    for nombre, campo in campos.items():
        campo.widget.attrs.update({"class": CLASE_CAMPO, **atributos_por_campo.get(nombre, {})})


class FormularioLogin(AuthenticationForm):
    """Inicio de sesión con usuario y contraseña (cuentas creadas por el admin)."""

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


class FormularioRecuperarClave(PasswordResetForm):
    """Pide el correo para enviar el enlace de nueva contraseña."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Correo electrónico"
        _estilizar(self.fields, {"email": {"autocomplete": "email", "autofocus": True}})


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

"""
Activación de cuentas creadas desde la página (/registro/).

La cuenta nace INACTIVA y se activa con el enlace que llega al correo. Así
se comprueba que el correo es real y le pertenece al estudiante (lo
necesita para recuperar la contraseña).
"""
import smtplib

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.mail import send_mail
from django.template import loader
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

# Errores posibles al hablar con el servidor de correo (clave mala, sin internet...)
ERRORES_CORREO = (smtplib.SMTPException, OSError)

# Para no reenviar el correo de activación en cada intento de login.
SEGUNDOS_ENTRE_REENVIOS = 5 * 60


class GeneradorTokenActivacion(PasswordResetTokenGenerator):
    """
    Token del enlace de activación. Usa otra "sal" que el de recuperar
    contraseña (uno no sirve para lo otro) e incluye is_active: después de
    activar la cuenta, el enlace deja de funcionar. Vence en
    PASSWORD_RESET_TIMEOUT (1 hora).
    """

    key_salt = "web.activacion.GeneradorTokenActivacion"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.password}{user.is_active}{user.correo_pendiente}{timestamp}"


token_activacion = GeneradorTokenActivacion()


def enviar_correo_activacion(request, usuario):
    """Envía el enlace de activación. Si el servidor de correo falla, el error sube."""
    enlace = request.build_absolute_uri(
        reverse(
            "activar_cuenta",
            kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(usuario.pk)),
                "token": token_activacion.make_token(usuario),
            },
        )
    )
    contexto = {"usuario": usuario, "enlace": enlace}
    send_mail(
        subject="UNEMI Guide AI · Activa tu cuenta",
        message=loader.render_to_string("registro/activar_email.txt", contexto),
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[usuario.email],
    )
    cache.set(f"activacion-enviada:{usuario.pk}", True, SEGUNDOS_ENTRE_REENVIOS)


def puede_reenviar(usuario):
    """True si pasaron al menos 5 minutos desde el último correo de activación."""
    return not cache.get(f"activacion-enviada:{usuario.pk}")


def ocultar_correo(correo):
    """juanperez@gmail.com -> ju*******@gmail.com (para mostrarlo en pantalla)."""
    nombre, _, dominio = correo.partition("@")
    visible = nombre[:2]
    return f"{visible}{'*' * max(len(nombre) - len(visible), 3)}@{dominio}"

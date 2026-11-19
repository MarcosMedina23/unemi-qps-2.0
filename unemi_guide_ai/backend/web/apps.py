"""Configuración de la app ``web``: Página única del estudiante, login y recuperación de cuenta."""
from django.apps import AppConfig
from django.conf import settings
from django.core import checks


def revisar_correo(app_configs, **kwargs):
    """
    Aviso al iniciar runserver si los correos de recuperación NO salen de verdad.

    Sin EMAIL_HOST_PASSWORD en backend/.env, Django usa el backend de consola:
    el correo se imprime en la terminal y nunca llega a la bandeja del estudiante.
    """
    if not settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
        return []
    return [
        checks.Warning(
            "Los correos de activar cuenta y recuperar contraseña/usuario NO se envían: solo se muestran en esta consola.",
            hint="Pon la contraseña de aplicación (16 letras) en EMAIL_HOST_PASSWORD de backend/.env "
            "y prueba con: python manage.py sendtestemail tu_correo@unemi.edu.ec",
            id="web.W001",
        )
    ]


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"
    verbose_name = "Web del estudiante"

    def ready(self):
        checks.register(revisar_correo)

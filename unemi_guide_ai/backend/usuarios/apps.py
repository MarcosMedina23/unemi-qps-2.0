"""
Configuración de la app ``usuarios``.

Cuentas de estudiantes (creadas solo por el administrador).
"""
from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "Usuarios"

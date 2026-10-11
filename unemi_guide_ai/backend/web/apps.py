"""Configuración de la app ``web``: Página única del estudiante, login y recuperación de cuenta."""
from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"
    verbose_name = "Web del estudiante"

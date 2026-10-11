"""
Configuración de la app ``vision``.

Reconocimiento de zona por foto (simulado hasta conectar YOLO).
"""
from django.apps import AppConfig


class VisionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vision"
    verbose_name = "Visión artificial"

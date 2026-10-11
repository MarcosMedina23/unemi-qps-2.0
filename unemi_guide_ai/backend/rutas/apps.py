"""
Configuración de la app ``rutas``.

Rutas registradas, cálculo con Dijkstra e historial de consultas.
"""
from django.apps import AppConfig


class RutasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rutas"
    verbose_name = "Rutas e historial"

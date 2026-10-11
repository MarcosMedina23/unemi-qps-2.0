"""
Rutas de la API de ``rutas``. Prefijo: /api/
"""
from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("historial", views.HistorialViewSet, basename="historial")

urlpatterns = [
    path("rutas/calcular/", views.CalcularRutaView.as_view(), name="api-calcular-ruta"),
    *router.urls,
]

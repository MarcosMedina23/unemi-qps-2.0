"""
Rutas de la API de ``zonas``. Prefijo: /api/
"""
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("zonas", views.ZonaViewSet, basename="zona")
router.register("destinos", views.DestinoViewSet, basename="destino")

urlpatterns = router.urls

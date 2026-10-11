"""
Rutas de la API de ``usuarios``. Prefijo: /api/usuarios/
"""
from django.urls import path

from . import views

urlpatterns = [
    path("yo/", views.UsuarioActualView.as_view(), name="api-usuario-actual"),
    path("carreras/", views.RankingCarrerasView.as_view(), name="api-ranking-carreras"),
]

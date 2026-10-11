"""
Vistas de la API de ``usuarios`` (solo lectura, requieren sesión).

    GET /api/usuarios/yo/        -> datos del usuario actual
    GET /api/usuarios/carreras/  -> carreras que más usan la app
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from zonas.views import MENSAJE_SIN_DATOS

from .models import Usuario
from .serializers import RankingCarreraSerializer, UsuarioActualSerializer


class UsuarioActualView(APIView):
    """Devuelve los datos del estudiante que inició sesión."""

    def get(self, request):
        return Response(UsuarioActualSerializer(request.user).data)


class RankingCarrerasView(APIView):
    """Top 5 de carreras según cuántos estudiantes usan la app."""

    def get(self, request):
        ranking = Usuario.objects.ranking_carreras(limite=5)
        if not ranking:
            return Response({"detalle": MENSAJE_SIN_DATOS}, status=status.HTTP_404_NOT_FOUND)
        return Response(RankingCarreraSerializer(ranking, many=True).data)

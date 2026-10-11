"""
Vistas de la API de ``rutas`` (requieren sesión).

    POST /api/rutas/calcular/   -> ruta entre una zona y un destino
    GET  /api/historial/        -> historial del usuario (más reciente primero)
    GET  /api/historial/{id}/   -> detalle de una consulta
    POST /api/historial/        -> guarda la ruta actual en el historial

Cada estudiante solo ve SU historial. Las rutas no se crean desde la API:
las registra el administrador en /admin/.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from zonas.views import SinDatosMixin

from .models import Historial, Ruta
from .serializers import (
    GuardarHistorialSerializer,
    HistorialSerializer,
    RutaSerializer,
    SolicitudRutaSerializer,
)
from .services import RutaNoEncontradaError, asegurar_camino

MENSAJE_SIN_RUTA = (
    "No encontramos una ruta disponible. No existe una conexión registrada "
    "entre tu ubicación y el destino seleccionado."
)


class CalcularRutaView(APIView):
    """
    Body JSON: {"origen_id": 1, "destino_id": 2}

    Busca la ruta que registró el administrador. Si su camino está vacío,
    lo completa con el algoritmo de Dijkstra antes de responder.
    """

    def post(self, request):
        solicitud = SolicitudRutaSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)

        ruta = (
            Ruta.objects.select_related("origen", "destino__zona")
            .filter(
                origen_id=solicitud.validated_data["origen_id"],
                destino_id=solicitud.validated_data["destino_id"],
            )
            .first()
        )
        if ruta is None:
            return Response({"detalle": MENSAJE_SIN_RUTA}, status=status.HTTP_404_NOT_FOUND)

        try:
            asegurar_camino(ruta)
        except RutaNoEncontradaError:
            return Response({"detalle": MENSAJE_SIN_RUTA}, status=status.HTTP_404_NOT_FOUND)

        return Response(RutaSerializer(ruta).data)


class HistorialViewSet(
    SinDatosMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Historial personal: listar, ver detalle y guardar (sin editar ni borrar)."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        # Filtro clave: cada usuario solo ve sus propias consultas.
        return Historial.objects.filter(usuario=self.request.user).select_related(
            "ruta__origen", "ruta__destino"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return GuardarHistorialSerializer
        return HistorialSerializer

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

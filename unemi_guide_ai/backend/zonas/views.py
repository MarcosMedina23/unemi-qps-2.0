"""
Vistas de la API de ``zonas`` (solo lectura, requieren sesión).

    GET  /api/zonas/              -> lista de zonas
    GET  /api/zonas/{id}/         -> detalle de una zona
    POST /api/zonas/reconocer/    -> reconoce la zona a partir de una foto
    GET  /api/destinos/           -> lista de destinos (?tipo=, ?q=, ?zona=)
    GET  /api/destinos/{id}/      -> detalle de un destino

No existen endpoints para crear, editar ni borrar: eso solo se hace en /admin/.
"""
import time

from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from vision.services import reconocer_zona
from vision.utils import UMBRAL_AMARILLO, clasificar_confianza

from .models import Destino, Zona
from .serializers import DestinoSerializer, FotoReconocimientoSerializer, ZonaSerializer

MENSAJE_SIN_DATOS = "No hay datos disponibles."


def respuesta_sin_datos():
    """Respuesta 404 estándar del proyecto: {"detalle": "No hay datos disponibles."}."""
    return Response({"detalle": MENSAJE_SIN_DATOS}, status=status.HTTP_404_NOT_FOUND)


class SinDatosMixin:
    """
    Si la lista está vacía o el objeto no existe, responde 404 con
    {"detalle": "No hay datos disponibles."} en lugar del mensaje de DRF.
    """

    def list(self, request, *args, **kwargs):
        if not self.filter_queryset(self.get_queryset()).exists():
            return respuesta_sin_datos()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Http404:
            return respuesta_sin_datos()


class ZonaViewSet(SinDatosMixin, viewsets.ReadOnlyModelViewSet):
    """Zonas del campus (comunes para todos los estudiantes)."""

    queryset = Zona.objects.all()
    serializer_class = ZonaSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="reconocer",
        parser_classes=[MultiPartParser, FormParser],
    )
    def reconocer(self, request):
        """
        Recibe una foto (multipart/form-data, campo ``foto``) y devuelve la
        zona reconocida con su semáforo:

            {"reconocida": true, "semaforo": "verde", "mensaje": "...",
             "confianza": 0.91, "zona": {...}, "detecciones": [...],
             "modo": "simulado", "simulado": true, "tiempo_ms": 42}
        """
        entrada = FotoReconocimientoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        # Se mide el tiempo para la métrica del proyecto (<= 5 s).
        inicio = time.perf_counter()
        resultado = reconocer_zona(entrada.validated_data["foto"])
        tiempo_ms = round((time.perf_counter() - inicio) * 1000)

        respuesta = {
            "confianza": resultado["confianza"],
            "zona": None,
            "detecciones": resultado["detecciones"],
            "modo": resultado["modo"],
            "simulado": resultado["simulado"],
            "tiempo_ms": tiempo_ms,
        }

        # Ninguna zona o confianza baja (< 0.65): semáforo rojo.
        if not resultado["zona"] or resultado["confianza"] < UMBRAL_AMARILLO:
            return Response({**respuesta, **clasificar_confianza(0.0, "")})

        zona = Zona.objects.filter(nombre__iexact=resultado["zona"]).first()
        if zona is None:
            # La IA devolvió una zona que el administrador aún no registró.
            return respuesta_sin_datos()

        semaforo = clasificar_confianza(resultado["confianza"], zona.nombre_completo)
        respuesta["zona"] = ZonaSerializer(zona, context={"request": request}).data
        return Response({**respuesta, **semaforo})


class DestinoViewSet(SinDatosMixin, viewsets.ReadOnlyModelViewSet):
    """Destinos, con filtros opcionales por tipo, texto y zona."""

    serializer_class = DestinoSerializer

    def get_queryset(self):
        destinos = Destino.objects.select_related("zona")
        parametros = self.request.query_params

        if tipo := parametros.get("tipo"):
            destinos = destinos.filter(tipo=tipo.lower())
        if texto := parametros.get("q"):
            destinos = destinos.filter(nombre__icontains=texto.strip())
        if zona := parametros.get("zona"):
            destinos = destinos.filter(zona_id=zona)
        return destinos

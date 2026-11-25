"""
Vistas de la API de ``zonas`` (solo lectura, requieren sesión).

    GET  /api/zonas/              -> lista de zonas
    GET  /api/zonas/{id}/         -> detalle de una zona
    POST /api/zonas/reconocer/    -> reconoce la zona a partir de una foto
    GET  /api/destinos/           -> lista de destinos (?tipo=, ?q=, ?zona=)
    GET  /api/destinos/{id}/      -> detalle de un destino

No existen endpoints para crear, editar ni borrar: eso solo se hace en /admin/.
"""
import re
import time
import unicodedata

from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from vision.calidad import analizar_calidad
from vision.services import reconocer_zona
from vision.utils import UMBRAL_AMARILLO, clasificar_confianza

from .grupos_ia import es_clase_sin_zona, grupo_de_clase, info_grupo
from .models import Destino, Zona
from .reconocimiento import Ubicacion, decidir
from .serializers import DestinoSerializer, FotoReconocimientoSerializer, ZonaSerializer

MENSAJE_SIN_DATOS = "No hay datos disponibles."
MENSAJE_NO_RECONOCIDA = "No pudimos reconocer tu ubicación, intenta con mejor iluminación."


# Nombres de la demo / del modelo de IA que en el campus real tienen otro nombre
# (los mismos equivalentes que usa rutas/management/commands/cargar_campus.py).
ALIAS_ZONAS = {"bloque a": "Bloque T (FACI)", "biblioteca central": "CRAI"}


def clave_nombre(nombre):
    """
    Nombre sin tildes, signos, espacios ni mayúsculas.

    Roboflow no acepta tildes ni paréntesis en las clases, así que el modelo
    devuelve "Bloque T -FACI-" o "Entrada de vehiculos". Con esta clave ambos
    coinciden con la zona real: "Bloque T (FACI)" -> "bloquetfaci".
    """
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sin_tildes.lower())


def buscar_zona(nombre):
    """
    Si el nombre es una clase de GRUPOS_IA ("Bloques V-W-X"), devuelve su zona
    principal ("Bloque W"). Si no: zona por nombre exacto; si no existe, por su equivalente en el campus real
    y, al final, ignorando tildes y signos (nombres de clases de Roboflow).
    """
    # Clase que agrupa varias zonas cercanas (zonas/grupos_ia.py): su zona principal.
    _, grupo = grupo_de_clase(nombre)
    if grupo is not None:
        nombre = grupo["zona"]

    zona = Zona.objects.filter(nombre__iexact=nombre).first()
    if zona is None and nombre.lower() in ALIAS_ZONAS:
        zona = Zona.objects.filter(nombre__iexact=ALIAS_ZONAS[nombre.lower()]).first()
    if zona is None:
        clave = clave_nombre(nombre)
        zona = next((z for z in Zona.objects.all() if clave_nombre(z.nombre) == clave), None)
    return zona


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
             "modo": "simulado", "simulado": true, "tiempo_ms": 42,
             "grupo": {"clase": "Bloque H", "incluye": [...], "cerca": [...]} | null,
             "motivo": null, "opciones": [], "calidad": {"nivel": "buena", ...}}

        Campos opcionales: ``latitud``, ``longitud`` y ``precision`` (GPS del celular).
        Si no se reconoce (400, semáforo rojo), ``motivo`` dice por qué
        ("dudosa", "foto_mala", "fuera_del_campus", "sin_deteccion") y
        ``opciones`` trae las zonas más probables para que el estudiante elija.
        Reglas en zonas/reconocimiento.py.
        """
        entrada = FotoReconocimientoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        foto = datos["foto"]
        ubicacion = None
        if datos.get("latitud") is not None and datos.get("longitud") is not None:
            ubicacion = Ubicacion(datos["latitud"], datos["longitud"], datos.get("precision"))

        # Se mide el tiempo para la métrica del proyecto (<= 5 s).
        inicio = time.perf_counter()
        calidad = analizar_calidad(foto)
        resultado = reconocer_zona(foto)
        decision = decidir(resultado, calidad, ubicacion, buscar_zona)
        tiempo_ms = round((time.perf_counter() - inicio) * 1000)

        respuesta = {
            "confianza": resultado["confianza"],
            "zona": None,
            "detecciones": resultado["detecciones"],
            "modo": resultado["modo"],
            "simulado": resultado["simulado"],
            "tiempo_ms": tiempo_ms,
            "grupo": None,
            # Nuevos: por qué no se reconoció, zonas para elegir y consejos de la foto.
            "motivo": decision["motivo"],
            "opciones": [
                {
                    "zona": ZonaSerializer(o["zona"], context={"request": request}).data,
                    "confianza": o["confianza"],
                    "distancia_m": o["distancia_m"],
                }
                for o in decision["opciones"]
            ],
            "calidad": calidad,
        }
        if resultado.get("aviso"):
            # Ej.: el microservicio de IA no respondió y se usó la simulación.
            respuesta["aviso"] = resultado["aviso"]

        if decision["motivo"] is not None:
            clase = resultado["zona"]
            if (
                decision["motivo"] == "sin_deteccion"
                and clase
                and resultado["confianza"] >= UMBRAL_AMARILLO
                and not es_clase_sin_zona(clase)
                and buscar_zona(clase) is None
            ):
                # La IA devolvió una zona que el administrador aún no registró.
                return respuesta_sin_datos()

            # No reconocida: 400 + semáforo rojo, con el mensaje y las opciones.
            detalle = (
                MENSAJE_NO_RECONOCIDA
                if decision["motivo"] in {"sin_deteccion", "foto_mala"}
                else decision["mensaje"]
            )
            return Response(
                {
                    **respuesta,
                    **clasificar_confianza(0.0, ""),
                    "mensaje": decision["mensaje"],
                    "detalle": detalle,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        zona = decision["zona"]
        respuesta["confianza"] = decision["confianza"]
        semaforo = clasificar_confianza(decision["confianza"], zona.nombre_completo)
        respuesta["zona"] = ZonaSerializer(zona, context={"request": request}).data
        # Lugares que abarca la clase detectada y lo que hay cerca (o None).
        clase = resultado["zona"]
        es_la_clase = clase and buscar_zona(clase) == zona
        respuesta["grupo"] = info_grupo(clase if es_la_clase else zona.nombre)
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

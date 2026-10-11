"""
Serializadores de la app ``rutas``.
"""
from django.core.exceptions import ValidationError as ErrorDjango
from rest_framework import serializers

from vision.utils import validar_foto
from zonas.serializers import DestinoSerializer

from .models import Historial, Ruta
from .services import construir_escena


class ZonaResumenSerializer(serializers.Serializer):
    """Datos mínimos de una zona dentro de una ruta."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    nombre_completo = serializers.CharField()


class RutaSerializer(serializers.ModelSerializer):
    """Ruta completa, con la escena 3D ya calculada por Python."""

    origen = ZonaResumenSerializer(read_only=True)
    destino = DestinoSerializer(read_only=True)
    tiempo_minutos = serializers.IntegerField(read_only=True)
    escena = serializers.SerializerMethodField()

    class Meta:
        model = Ruta
        fields = ["id", "origen", "destino", "distancia", "tiempo_minutos", "camino_json", "escena"]
        read_only_fields = fields

    def get_escena(self, ruta):
        return construir_escena(ruta)


class SolicitudRutaSerializer(serializers.Serializer):
    """Body de POST /api/rutas/calcular/."""

    origen_id = serializers.IntegerField(min_value=1)
    destino_id = serializers.IntegerField(min_value=1)


class RutaResumenSerializer(serializers.ModelSerializer):
    """Ruta resumida para el historial."""

    origen = ZonaResumenSerializer(read_only=True)
    destino = serializers.SerializerMethodField()
    tiempo_minutos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ruta
        fields = ["id", "origen", "destino", "distancia", "tiempo_minutos"]
        read_only_fields = fields

    def get_destino(self, ruta):
        return {"id": ruta.destino_id, "nombre": ruta.destino.nombre}


class HistorialSerializer(serializers.ModelSerializer):
    """Consulta del historial del estudiante."""

    ruta = RutaResumenSerializer(read_only=True)

    class Meta:
        model = Historial
        fields = ["id", "ruta", "fecha", "foto_origen"]
        read_only_fields = fields


class GuardarHistorialSerializer(serializers.ModelSerializer):
    """Body de POST /api/historial/ (botón «Guardar en mi historial»)."""

    ruta_id = serializers.PrimaryKeyRelatedField(queryset=Ruta.objects.all(), source="ruta")
    foto_origen = serializers.ImageField(required=False)

    class Meta:
        model = Historial
        fields = ["id", "ruta_id", "foto_origen"]

    def validate_foto_origen(self, foto):
        try:
            validar_foto(foto)
        except ErrorDjango as error:
            raise serializers.ValidationError(error.messages) from error
        return foto

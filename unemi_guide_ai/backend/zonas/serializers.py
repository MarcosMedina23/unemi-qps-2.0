"""
Serializadores de la app ``zonas``.
"""
from django.core.exceptions import ValidationError as ErrorDjango
from rest_framework import serializers

from vision.utils import validar_foto

from .models import Destino, Zona


class ZonaSerializer(serializers.ModelSerializer):
    """Zona del campus."""

    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Zona
        fields = [
            "id",
            "nombre",
            "descripcion",
            "nombre_completo",
            "latitud",
            "longitud",
            "imagen_referencia",
        ]
        read_only_fields = fields


class DestinoSerializer(serializers.ModelSerializer):
    """Destino con el nombre legible de su tipo y de su zona."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    zona_nombre = serializers.CharField(source="zona.nombre", read_only=True)

    class Meta:
        model = Destino
        fields = [
            "id",
            "nombre",
            "tipo",
            "tipo_display",
            "zona",
            "zona_nombre",
            "latitud",
            "longitud",
        ]
        read_only_fields = fields


class FotoReconocimientoSerializer(serializers.Serializer):
    """Valida la foto enviada para reconocer la zona."""

    foto = serializers.ImageField()

    def validate_foto(self, foto):
        try:
            validar_foto(foto)
        except ErrorDjango as error:
            raise serializers.ValidationError(error.messages) from error
        return foto

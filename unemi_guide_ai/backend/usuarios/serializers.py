"""
Serializadores de la app ``usuarios`` (solo lectura).
"""
from rest_framework import serializers

from .models import Usuario


class UsuarioActualSerializer(serializers.ModelSerializer):
    """Datos del usuario que inició sesión (sin información sensible)."""

    nombre_para_mostrar = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "nombre_para_mostrar",
            "es_estudiante",
            "carrera",
            "semestre",
        ]
        read_only_fields = fields


class RankingCarreraSerializer(serializers.Serializer):
    """Una fila del ranking de carreras."""

    carrera = serializers.CharField()
    total = serializers.IntegerField()
    porcentaje = serializers.FloatField()
    proporcion = serializers.FloatField()

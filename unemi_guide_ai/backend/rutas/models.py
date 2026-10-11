"""
Modelos de la app ``rutas``.

- Pasillo:   punto de cruce del campus (nodo del grafo).
- Conexion:  camino peatonal entre dos pasillos (arista del grafo).
- Ruta:      camino registrado por el administrador entre una zona y un destino.
- Historial: registro de las rutas que consultó cada estudiante.
"""
import math

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from vision.utils import distancia_metros
from zonas.models import VALIDADORES_LATITUD, VALIDADORES_LONGITUD, Destino, Zona

# Velocidad promedio caminando: 1.4 m/s (84 m/min), valor estándar peatonal.
VELOCIDAD_CAMINATA_M_POR_MIN = 1.4 * 60


class Pasillo(models.Model):
    """
    Punto de cruce por donde pasan las rutas (ej.: "Plaza Central").

    Cada zona se conecta automáticamente a sus 2 pasillos más cercanos.
    Si no hay pasillos registrados, se usan los de rutas/mapa_campus.py.
    """

    codigo = models.CharField("código", max_length=10, unique=True, help_text="Ej.: P-01")
    nombre = models.CharField(max_length=100)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, validators=VALIDADORES_LATITUD)
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, validators=VALIDADORES_LONGITUD
    )

    class Meta:
        verbose_name = "pasillo"
        verbose_name_plural = "pasillos del campus"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Conexion(models.Model):
    """Camino peatonal entre dos pasillos (en ambos sentidos)."""

    pasillo_a = models.ForeignKey(
        Pasillo, on_delete=models.CASCADE, related_name="conexiones_salientes"
    )
    pasillo_b = models.ForeignKey(
        Pasillo, on_delete=models.CASCADE, related_name="conexiones_entrantes"
    )
    distancia_m = models.FloatField(
        "distancia (m)",
        null=True,
        blank=True,
        help_text="Déjala vacía para calcularla en línea recta. "
        "Escríbela si el camino real da un rodeo.",
    )

    class Meta:
        verbose_name = "conexión"
        verbose_name_plural = "conexiones entre pasillos"
        constraints = [
            models.UniqueConstraint(fields=["pasillo_a", "pasillo_b"], name="conexion_unica"),
            models.CheckConstraint(
                condition=~models.Q(pasillo_a=models.F("pasillo_b")),
                name="conexion_entre_pasillos_distintos",
            ),
        ]

    def __str__(self):
        return f"{self.pasillo_a.nombre} ↔ {self.pasillo_b.nombre}"

    def clean(self):
        if self.pasillo_a_id and self.pasillo_a_id == self.pasillo_b_id:
            raise ValidationError("Una conexión debe unir dos pasillos distintos.")

    def save(self, *args, **kwargs):
        # Si no se indicó la distancia, se calcula en línea recta (Haversine).
        if self.distancia_m is None:
            self.distancia_m = round(
                distancia_metros(
                    self.pasillo_a.latitud,
                    self.pasillo_a.longitud,
                    self.pasillo_b.latitud,
                    self.pasillo_b.longitud,
                ),
                1,
            )
        super().save(*args, **kwargs)


class Ruta(models.Model):
    """
    Ruta desde una zona (origen) hasta un destino.

    ``camino_json`` es la lista de puntos (waypoints) que se dibuja en 3D:

        [{"lat": -2.1497, "lng": -79.6036}, {"lat": -2.1495, "lng": -79.6031}, ...]

    Si el administrador deja la distancia o el camino vacíos, se calculan
    automáticamente (de forma simulada) al guardar desde el admin.
    """

    origen = models.ForeignKey(Zona, on_delete=models.PROTECT, related_name="rutas_salientes")
    destino = models.ForeignKey(Destino, on_delete=models.PROTECT, related_name="rutas_entrantes")
    distancia = models.FloatField(
        "distancia (m)",
        null=True,
        blank=True,
        help_text="En metros. Déjala vacía para calcularla automáticamente.",
    )
    camino_json = models.JSONField(
        "camino (waypoints)",
        default=list,
        blank=True,
        help_text="Lista de puntos {lat, lng}. Déjala vacía para generarla automáticamente.",
    )

    class Meta:
        verbose_name = "ruta"
        verbose_name_plural = "rutas"
        ordering = ["origen__nombre", "destino__nombre"]
        constraints = [
            # Solo una ruta registrada por cada par origen-destino.
            models.UniqueConstraint(fields=["origen", "destino"], name="ruta_unica_por_par"),
        ]

    def __str__(self):
        return f"{self.origen} → {self.destino.nombre}"

    @property
    def tiempo_minutos(self):
        """Minutos aproximados caminando (mínimo 1)."""
        if not self.distancia:
            return None
        return max(1, math.ceil(self.distancia / VELOCIDAD_CAMINATA_M_POR_MIN))


class Historial(models.Model):
    """Consulta de ruta guardada por un estudiante. Se genera con el uso."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="historial"
    )
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="consultas")
    fecha = models.DateTimeField(auto_now_add=True)
    foto_origen = models.ImageField(
        "foto de origen",
        upload_to="historial/%Y/%m/",
        blank=True,
        help_text="Foto que tomó el estudiante para reconocer la zona.",
    )

    class Meta:
        verbose_name = "consulta del historial"
        verbose_name_plural = "historial"
        ordering = ["-fecha"]  # Más reciente primero.

    def __str__(self):
        return f"{self.usuario} · {self.ruta} · {self.fecha:%d/%m/%Y %H:%M}"

"""
Modelos de la app ``zonas``.

- Zona:    área del campus que la visión artificial puede reconocer.
- Destino: lugar concreto al que el estudiante quiere llegar.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Validadores reutilizables para coordenadas geográficas.
VALIDADORES_LATITUD = [MinValueValidator(-90), MaxValueValidator(90)]
VALIDADORES_LONGITUD = [MinValueValidator(-180), MaxValueValidator(180)]


class Zona(models.Model):
    """
    Zona del campus (ej.: "Bloque A").

    El ``nombre`` debe coincidir con la clase que devuelve el modelo de
    visión artificial (YOLO) para que el reconocimiento la encuentre.
    """

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(
        "descripción",
        max_length=200,
        blank=True,
        help_text="Ej.: Facultad de Ciencias e Ingeniería",
    )
    latitud = models.DecimalField(max_digits=9, decimal_places=6, validators=VALIDADORES_LATITUD)
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, validators=VALIDADORES_LONGITUD
    )
    imagen_referencia = models.ImageField(
        "imagen de referencia",
        upload_to="zonas/",
        blank=True,
        help_text="Foto de la fachada (opcional).",
    )

    class Meta:
        verbose_name = "zona"
        verbose_name_plural = "zonas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def nombre_completo(self):
        """Ej.: "Bloque A — Facultad de Ciencias e Ingeniería"."""
        return f"{self.nombre} — {self.descripcion}" if self.descripcion else self.nombre


class Destino(models.Model):
    """Lugar específico dentro de una zona (aula, laboratorio, etc.)."""

    class Tipo(models.TextChoices):
        AULA = "aula", "Aula"
        LABORATORIO = "laboratorio", "Laboratorio"
        BIBLIOTECA = "biblioteca", "Biblioteca"
        OFICINA = "oficina", "Oficina"

    nombre = models.CharField(max_length=120)
    zona = models.ForeignKey(Zona, on_delete=models.PROTECT, related_name="destinos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.AULA)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, validators=VALIDADORES_LATITUD)
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, validators=VALIDADORES_LONGITUD
    )

    class Meta:
        verbose_name = "destino"
        verbose_name_plural = "destinos"
        ordering = ["nombre"]
        constraints = [
            # No puede haber dos destinos con el mismo nombre en una zona.
            models.UniqueConstraint(fields=["zona", "nombre"], name="destino_unico_por_zona"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.zona})"

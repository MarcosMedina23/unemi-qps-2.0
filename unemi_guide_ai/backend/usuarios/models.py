"""
Modelos de la app ``usuarios``.

Regla de negocio: NO hay registro público. El administrador crea las
cuentas de los estudiantes desde /admin/ (sin "Staff status"), por lo que
un estudiante nunca puede entrar al admin ni modificar datos.
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count

# Carreras disponibles al crear un estudiante en el admin. Se usa una
# lista cerrada para que el ranking no se divida por diferencias de
# escritura ("Software" vs "Ing. Software"). Revisar contra la oferta
# académica vigente de la UNEMI.
_NOMBRES_CARRERAS = (
    "Ingeniería de Software",
    "Tecnologías de la Información",
    "Ingeniería Industrial",
    "Ingeniería Ambiental",
    "Biotecnología",
    "Administración de Empresas",
    "Contabilidad y Auditoría",
    "Economía",
    "Turismo",
    "Derecho",
    "Comunicación",
    "Psicología",
    "Trabajo Social",
    "Enfermería",
    "Nutrición y Dietética",
    "Educación Básica",
    "Educación Inicial",
    "Pedagogía de la Actividad Física y Deporte",
    "Otra",
)
CARRERAS_UNEMI = [(nombre, nombre) for nombre in _NOMBRES_CARRERAS]


class UsuarioManager(UserManager):
    """Manager con consultas propias del proyecto."""

    def ranking_carreras(self, limite=5):
        """
        Carreras con más estudiantes activos, de mayor a menor.

        Equivale a:
            SELECT carrera, COUNT(*) AS total FROM usuarios_usuario
            WHERE es_estudiante AND is_active AND carrera <> ''
            GROUP BY carrera ORDER BY total DESC, carrera LIMIT 5;
        """
        filas = list(
            self.filter(es_estudiante=True, is_active=True)
            .exclude(carrera="")
            .values("carrera")
            .annotate(total=Count("id"))
            .order_by("-total", "carrera")
        )
        if not filas:
            return []

        total_estudiantes = sum(fila["total"] for fila in filas)
        maximo = filas[0]["total"]
        for fila in filas:
            fila["porcentaje"] = round(fila["total"] * 100 / total_estudiantes, 1)
            # Proporción respecto a la carrera líder (para dibujar la barra).
            fila["proporcion"] = round(fila["total"] / maximo, 3)
        return filas[:limite]


class Usuario(AbstractUser):
    """
    Usuario del sistema.

    Hereda de AbstractUser: username, password, first_name, last_name,
    email, is_staff, is_active, date_joined, etc.
    """

    es_estudiante = models.BooleanField(
        "es estudiante",
        default=True,
        help_text="Márcalo para estudiantes. Desmárcalo para personal administrativo.",
    )
    carrera = models.CharField(max_length=120, blank=True, choices=CARRERAS_UNEMI)
    semestre = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Del 1 al 10.",
    )

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def nombre_para_mostrar(self):
        """Nombre que se muestra en la barra superior de la web."""
        return self.first_name or self.username

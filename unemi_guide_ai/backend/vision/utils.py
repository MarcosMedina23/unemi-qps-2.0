"""
Utilidades de la app ``vision``: geometría, validación de fotos y semáforo.

Son funciones de Python puro (no usan la base de datos), fáciles de probar.
"""
import math

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

# Radio medio de la Tierra en metros.
RADIO_TIERRA_M = 6_371_000
METROS_POR_GRADO = math.pi * RADIO_TIERRA_M / 180

# Umbrales del semáforo de reconocimiento.
UMBRAL_VERDE = 0.85
UMBRAL_AMARILLO = 0.65

FORMATOS_FOTO_PERMITIDOS = {"JPEG", "PNG", "WEBP"}


# ----------------------------------------------------------------------
# Geometría
# ----------------------------------------------------------------------
def distancia_metros(lat1, lng1, lat2, lng2):
    """Distancia en metros entre dos coordenadas (fórmula de Haversine)."""
    lat1, lng1, lat2, lng2 = (math.radians(float(valor)) for valor in (lat1, lng1, lat2, lng2))
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(a))


def a_metros_locales(lat, lng, lat_referencia, lng_referencia):
    """
    Convierte una coordenada a metros (x, z) respecto a un punto de referencia.

    Convención (la misma de la escena 3D): X = este, Z = sur.
    Para las distancias de un campus, la proyección equirectangular basta.
    """
    factor = math.cos(math.radians(float(lat_referencia)))
    x = (float(lng) - float(lng_referencia)) * METROS_POR_GRADO * factor
    z = -(float(lat) - float(lat_referencia)) * METROS_POR_GRADO
    return x, z


def a_coordenadas(x, z, lat_referencia, lng_referencia):
    """Operación inversa de ``a_metros_locales``: metros (x, z) → (lat, lng)."""
    factor = math.cos(math.radians(float(lat_referencia)))
    lat = float(lat_referencia) - z / METROS_POR_GRADO
    lng = float(lng_referencia) + x / (METROS_POR_GRADO * factor)
    return round(lat, 6), round(lng, 6)


# ----------------------------------------------------------------------
# Validación de fotos
# ----------------------------------------------------------------------
def validar_foto(archivo):
    """
    Verifica que el archivo sea una imagen JPG, PNG o WEBP y no supere el
    tamaño máximo definido en settings.TAMANO_MAXIMO_FOTO_MB.

    Raises:
        ValidationError: con un mensaje claro para el estudiante.
    """
    maximo_bytes = settings.TAMANO_MAXIMO_FOTO_MB * 1024 * 1024
    if archivo.size > maximo_bytes:
        raise ValidationError(
            f"La foto supera el máximo de {settings.TAMANO_MAXIMO_FOTO_MB} MB."
        )
    try:
        with Image.open(archivo) as imagen:
            formato = imagen.format
            imagen.verify()  # Detecta archivos dañados.
    except (UnidentifiedImageError, OSError) as error:
        raise ValidationError("El archivo no es una imagen válida.") from error
    finally:
        archivo.seek(0)  # Permite volver a leer el archivo después.

    if formato not in FORMATOS_FOTO_PERMITIDOS:
        raise ValidationError("Formato no soportado. Usa una foto JPG, PNG o WEBP.")


# ----------------------------------------------------------------------
# Semáforo de reconocimiento
# ----------------------------------------------------------------------
def clasificar_confianza(confianza, nombre_zona):
    """
    Clasifica el resultado del reconocimiento.

    Returns:
        dict con:
            semaforo:   "verde" (>= 0.85), "amarillo" (0.65 a 0.85) o "rojo" (< 0.65)
            reconocida: True si el estudiante puede continuar con esa zona
            mensaje:    texto que se muestra en pantalla
    """
    if confianza >= UMBRAL_VERDE:
        return {
            "semaforo": "verde",
            "reconocida": True,
            "mensaje": f"¡Zona reconocida! Estás en: {nombre_zona}.",
        }
    if confianza >= UMBRAL_AMARILLO:
        return {
            "semaforo": "amarillo",
            "reconocida": True,
            "mensaje": f"Zona detectada con confianza media. Estás en: {nombre_zona}.",
        }
    return {
        "semaforo": "rojo",
        "reconocida": False,
        "mensaje": "No pudimos reconocer tu ubicación. Intenta con otra foto.",
    }

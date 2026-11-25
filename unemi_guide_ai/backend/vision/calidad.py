"""
Calidad de la foto: ¿está movida, oscura, quemada por el sol, tapada o es muy pequeña?

Solo usa Pillow (sin OpenCV) para que funcione en el servidor pequeño.
La foto se reduce a 512 px para que las medidas no dependan del celular.

    analizar_calidad(foto) -> {"nivel": "buena" | "regular" | "mala",
                               "problemas": ["borrosa", ...],
                               "consejos": ["La foto salió movida...", ...]}

- "mala":    casi seguro la IA no podrá reconocerla (se pide otra foto, salvo que
             la IA la reconozca con confianza alta).
- "regular": se reconoce igual y se muestra el consejo para la próxima.
"""
from PIL import Image, ImageFilter, ImageOps, ImageStat

LADO_ANALISIS = 512

# Umbrales (calibrados con fotos del celular reducidas a 512 px).
LADO_MINIMO_PX = 240         # menos que esto: foto muy pequeña
CONTRASTE_TAPADA = 12        # desviación de grises: casi un solo color (lente tapado)
BRILLO_MUY_OSCURA = 35       # promedio de grises 0-255
BRILLO_OSCURA = 60
QUEMADA_MALA = 0.55          # fracción de píxeles casi blancos (un cielo nublado
QUEMADA_REGULAR = 0.35       # puede ocupar un tercio de la foto sin que sea mala)
NITIDEZ_MALA = 5             # varianza del Laplaciano: nítida 40+, algo movida ~7,
NITIDEZ_REGULAR = 15         # muy movida o desenfocada <= 3

CONSEJOS = {
    "pequena": "La foto es muy pequeña. Tómala con la cámara del celular, sin recortarla.",
    "tapada": "La foto se ve casi de un solo color. Revisa que nada tape la cámara "
              "y apunta a un bloque, letrero o entrada.",
    "oscura": "La foto está muy oscura. Revisa que nada tape la cámara y busca más luz "
              "(cerca de una lámpara o de día).",
    "quemada": "Hay demasiada luz (sol de frente). Ponte de espaldas al sol y vuelve a tomarla.",
    "borrosa": "La foto salió movida o desenfocada. Sostén el celular firme, "
               "toca la pantalla para enfocar y vuelve a tomarla.",
}

# Kernel del Laplaciano (detecta bordes). offset=128 para no perder los negativos.
_LAPLACIANO = ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=128)


def medir(imagen):
    """Medidas de una imagen de Pillow (ya abierta)."""
    imagen = ImageOps.exif_transpose(imagen)
    ancho, alto = imagen.size
    gris = imagen.convert("L")
    gris.thumbnail((LADO_ANALISIS, LADO_ANALISIS))

    estadisticas = ImageStat.Stat(gris)
    histograma = gris.histogram()
    total = sum(histograma) or 1
    # Pillow deja sin filtrar el borde de 1 px: se recorta para que no altere la medida.
    bordes = gris.filter(_LAPLACIANO)
    bordes = bordes.crop((1, 1, max(bordes.width - 1, 2), max(bordes.height - 1, 2)))
    return {
        "lado_menor": min(ancho, alto),
        "brillo": estadisticas.mean[0],
        "contraste": estadisticas.stddev[0],
        "quemada": sum(histograma[250:]) / total,
        "nitidez": ImageStat.Stat(bordes).var[0],
    }


def evaluar(medidas):
    """Problemas y nivel a partir de las medidas."""
    graves, leves = [], []
    if medidas["lado_menor"] < LADO_MINIMO_PX:
        graves.append("pequena")
    if medidas["brillo"] < BRILLO_MUY_OSCURA:
        # Muy oscura (de noche o con el dedo en la cámara): basta con un consejo.
        graves.append("oscura")
    elif medidas["contraste"] < CONTRASTE_TAPADA:
        # Casi un solo color: todo blanco = sol de frente; si no, algo tapa la cámara.
        graves.append("quemada" if medidas["brillo"] > 200 else "tapada")
    else:
        if medidas["brillo"] < BRILLO_OSCURA:
            leves.append("oscura")
        if medidas["quemada"] > QUEMADA_MALA:
            graves.append("quemada")
        elif medidas["quemada"] > QUEMADA_REGULAR:
            leves.append("quemada")
        if medidas["nitidez"] < NITIDEZ_MALA:
            graves.append("borrosa")
        elif medidas["nitidez"] < NITIDEZ_REGULAR:
            leves.append("borrosa")

    problemas = graves + leves
    nivel = "mala" if graves else "regular" if leves else "buena"
    return {
        "nivel": nivel,
        "problemas": problemas,
        "consejos": [CONSEJOS[p] for p in problemas],
    }


def analizar_calidad(foto):
    """Analiza un archivo subido (deja el puntero al inicio para volver a leerlo)."""
    try:
        with Image.open(foto) as imagen:
            return evaluar(medir(imagen))
    except OSError:
        return {"nivel": "buena", "problemas": [], "consejos": []}  # La valida validar_foto
    finally:
        foto.seek(0)

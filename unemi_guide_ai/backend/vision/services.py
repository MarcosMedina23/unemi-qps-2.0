"""
Servicios de visión artificial de UNEMI Guide AI.

``reconocer_zona(foto)`` es la única función que usan las vistas.
Elige el modo automáticamente, en este orden:

    1. Microservicio ia_service  -> si IA_SERVICE_URL está en el .env
                                    (si no responde, usa la simulación; con
                                    IA_PERMITIR_SIMULACION=False responde
                                    "no_disponible" y no inventa una zona).
    2. Modelos locales           -> si existen yolo_zone.pt, zone_classifier.pkl
                                    y tfidf.pkl en backend/ml/models/.
    3. Simulación                -> en cualquier otro caso.

Cómo se decide la zona con los modelos (2 pasos):
    a) YOLOv8 detecta OBJETOS en la foto (letrero, puerta, escalera...).
    b) Un clasificador TF-IDF + RandomForest decide la ZONA a partir de
       esos objetos (ej.: "letrero escalera puerta" -> Bloque A).

Los 3 modos devuelven un diccionario con el MISMO formato:
    {"zona": "Bloque A", "confianza": 0.91, "detecciones": [...],
     "modo": "simulado" | "local" | "ia_service", "simulado": True/False}
"""
import importlib.util
import logging
import random

import requests
from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Zona que devuelve la simulación si todavía no hay zonas registradas en el admin.
ZONA_SIMULADA = "Bloque A"


def elegir_zona_simulada():
    """Una zona registrada al azar (cada foto te ubica en un lugar distinto)."""
    from zonas.models import Zona  # Import aquí para no crear un ciclo al cargar Django

    nombre = Zona.objects.order_by("?").values_list("nombre", flat=True).first()
    return nombre or ZONA_SIMULADA

# Rango de confianza que inventa la simulación.
CONFIANZA_MINIMA_SIMULADA = 0.65
CONFIANZA_MAXIMA_SIMULADA = 0.98

# Confianza mínima para que YOLO cuente un objeto como detectado.
CONFIANZA_MINIMA_DETECCION = 0.25

AVISO_IA_NO_DISPONIBLE = "El servicio de IA no respondió; se usó el reconocimiento simulado."

# Aquí guardamos los modelos ya cargados para no leerlos del disco en cada foto.
# La primera foto tarda más; las siguientes reutilizan lo que está aquí.
modelos_en_memoria = {}


def armar_resultado(zona, confianza, detecciones, modo):
    """Crea el diccionario de respuesta (igual para los 3 modos)."""
    return {
        "zona": zona,
        "confianza": confianza,
        "detecciones": detecciones,
        "modo": modo,
        "simulado": modo == "simulado",
    }


def resultado_no_disponible():
    """La IA no respondió y la simulación está apagada (IA_PERMITIR_SIMULACION=False)."""
    resultado = armar_resultado(None, 0.0, [], "ia_service")
    resultado["no_disponible"] = True
    return resultado


def libreria_instalada(nombre):
    """True si la librería de Python está instalada en el venv."""
    return importlib.util.find_spec(nombre) is not None


# ----------------------------------------------------------------------
# Modo 3: simulación
# ----------------------------------------------------------------------
def reconocer_zona_simulado(foto, cantidad=5):
    """
    Inventa un resultado con números al azar (sirve mientras no hay modelo).

    Args:
        foto: archivo de imagen subido.
        cantidad: cuántas cajas (detecciones) inventar.
    """
    with Image.open(foto) as imagen:
        ancho, alto = imagen.size
    foto.seek(0)  # Regresamos al inicio para poder leer la foto otra vez.

    zona = elegir_zona_simulada()
    confianza = round(random.uniform(CONFIANZA_MINIMA_SIMULADA, CONFIANZA_MAXIMA_SIMULADA), 2)

    detecciones = []
    for _ in range(cantidad):
        x1 = random.randint(0, ancho // 2)
        y1 = random.randint(0, alto // 2)
        x2 = random.randint(x1 + 1, ancho)
        y2 = random.randint(y1 + 1, alto)
        confianza_caja = round(random.uniform(CONFIANZA_MINIMA_SIMULADA, confianza), 2)
        detecciones.append(
            {"clase": zona, "confianza": confianza_caja, "caja": [x1, y1, x2, y2]}
        )

    # Ordenamos de mayor a menor confianza; la primera es la principal.
    detecciones.sort(key=lambda d: d["confianza"], reverse=True)
    detecciones[0]["confianza"] = confianza

    return armar_resultado(zona, confianza, detecciones, "simulado")


# ----------------------------------------------------------------------
# Clasificador TF-IDF + RandomForest (lo usan los modos 1 y 2)
# ----------------------------------------------------------------------
def clasificador_disponible():
    """True si están los archivos del clasificador y sus librerías."""
    return (
        settings.MODELO_CLASIFICADOR.exists()
        and settings.MODELO_TFIDF.exists()
        and libreria_instalada("joblib")
        and libreria_instalada("sklearn")
    )


def cargar_clasificador():
    """Carga (una sola vez) el clasificador y el vectorizador TF-IDF."""
    if "clasificador" not in modelos_en_memoria:
        import joblib  # Se importa aquí porque solo hace falta si hay modelo.

        modelos_en_memoria["clasificador"] = joblib.load(settings.MODELO_CLASIFICADOR)
        modelos_en_memoria["tfidf"] = joblib.load(settings.MODELO_TFIDF)
    return modelos_en_memoria["clasificador"], modelos_en_memoria["tfidf"]


def predecir_zona(objetos, clasificador, vectorizador):
    """
    Decide la zona a partir de los nombres de los objetos detectados.

    Ejemplo: ["letrero", "escalera"] -> ("Bloque A", 0.87)
    """
    texto = " ".join(objetos)  # "letrero escalera"
    probabilidades = clasificador.predict_proba(vectorizador.transform([texto]))[0]
    posicion_mayor = int(probabilidades.argmax())  # Índice de la zona más probable
    zona = str(clasificador.classes_[posicion_mayor])
    confianza = round(float(probabilidades[posicion_mayor]), 2)
    return zona, confianza


# ----------------------------------------------------------------------
# Modo 2: modelos locales (YOLOv8 + clasificador)
# ----------------------------------------------------------------------
def modelos_locales_disponibles():
    """True si están YOLO, el clasificador y la librería ultralytics."""
    return (
        settings.MODELO_YOLO.exists()
        and libreria_instalada("ultralytics")
        and clasificador_disponible()
    )


def cargar_yolo():
    """Carga (una sola vez) el modelo YOLOv8."""
    if "yolo" not in modelos_en_memoria:
        from ultralytics import YOLO  # Librería pesada: solo se importa si hace falta.

        modelos_en_memoria["yolo"] = YOLO(str(settings.MODELO_YOLO))
    return modelos_en_memoria["yolo"]


def detectar_objetos(imagen):
    """
    Detecta objetos con YOLOv8.

    Returns:
        Lista de {"clase": "puerta", "confianza": 0.8, "caja": [x1, y1, x2, y2]}
    """
    resultado = cargar_yolo()(imagen, conf=CONFIANZA_MINIMA_DETECCION, verbose=False)[0]
    cajas = resultado.boxes

    detecciones = []
    for i in range(len(cajas)):
        numero_clase = int(cajas.cls[i])
        detecciones.append(
            {
                "clase": resultado.names[numero_clase],
                "confianza": round(float(cajas.conf[i]), 2),
                "caja": [round(float(valor)) for valor in cajas.xyxy[i]],
            }
        )
    return detecciones


def reconocer_zona_modelo_local(foto):
    """Reconocimiento real con los modelos entrenados en backend/ml/."""
    with Image.open(foto) as archivo:
        # exif_transpose endereza las fotos que el celular guarda giradas.
        imagen = ImageOps.exif_transpose(archivo).convert("RGB")
    foto.seek(0)

    detecciones = detectar_objetos(imagen)
    if not detecciones:
        # Sin objetos no hay forma de decidir: el semáforo quedará en rojo.
        return armar_resultado(None, 0.0, [], "local")

    nombres_objetos = [d["clase"] for d in detecciones]
    clasificador, vectorizador = cargar_clasificador()
    zona, confianza = predecir_zona(nombres_objetos, clasificador, vectorizador)
    return armar_resultado(zona, confianza, detecciones, "local")


# ----------------------------------------------------------------------
# Modo 1: microservicio ia_service (carpeta ia_service/)
# ----------------------------------------------------------------------
def zona_desde_detecciones(detecciones):
    """
    Decide la zona con lo que devolvió el microservicio.

    - Si hay clasificador entrenado: lo usamos (YOLO detectó objetos).
    - Si no: tomamos la detección con mayor confianza (best.pt entrenado
      directamente con las zonas como clases: "Bloque A", "Biblioteca"...).
    """
    if not detecciones:
        return None, 0.0

    if clasificador_disponible():
        clasificador, vectorizador = cargar_clasificador()
        nombres_objetos = [d["clase"] for d in detecciones]
        return predecir_zona(nombres_objetos, clasificador, vectorizador)

    mejor = max(detecciones, key=lambda d: d["confianza"])
    return mejor["clase"], round(float(mejor["confianza"]), 2)


def reconocer_zona_con_ia(foto):
    """
    Envía la foto al microservicio ia_service.

    Si no responde, tarda demasiado o da error, usamos la simulación
    para que la app NO se caiga (y avisamos con un mensaje).
    """
    contenido = foto.read()
    foto.seek(0)
    nombre = foto.name or "foto.jpg"
    tipo = foto.content_type or "image/jpeg"

    try:
        respuesta = requests.post(
            settings.IA_SERVICE_URL,
            files={"foto": (nombre, contenido, tipo)},
            timeout=settings.TIEMPO_MAXIMO_RECONOCIMIENTO_S,
        )
        respuesta.raise_for_status()  # Lanza error si el código es 4xx o 5xx.
        detecciones = respuesta.json()["detecciones"]
    except (requests.RequestException, ValueError, KeyError) as error:
        if not settings.IA_PERMITIR_SIMULACION:
            logger.warning("ia_service no disponible (%s).", error)
            return resultado_no_disponible()
        logger.warning("ia_service no disponible (%s). Se usa la simulación.", error)
        resultado = reconocer_zona_simulado(foto)
        resultado["aviso"] = AVISO_IA_NO_DISPONIBLE
        return resultado

    zona, confianza = zona_desde_detecciones(detecciones)
    return armar_resultado(zona, confianza, detecciones, "ia_service")


# ----------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------
def reconocer_zona(foto):
    """Única función que usan las vistas. Elige el modo automáticamente."""
    if settings.IA_SERVICE_URL:
        return reconocer_zona_con_ia(foto)
    if modelos_locales_disponibles():
        return reconocer_zona_modelo_local(foto)
    if not settings.IA_PERMITIR_SIMULACION:
        return resultado_no_disponible()
    return reconocer_zona_simulado(foto)

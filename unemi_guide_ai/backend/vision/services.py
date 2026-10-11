"""
Servicios de visión artificial de UNEMI Guide AI.

``reconocer_zona(foto)`` elige el modo automáticamente:

    1. Microservicio ia_service   si settings.IA_SERVICE_URL está definido.
    2. Modelos locales            si existen los archivos de backend/ml/models/
                                  (yolo_zone.pt, zone_classifier.pkl, tfidf.pkl)
                                  y están instaladas ultralytics y scikit-learn.
    3. Simulación                 en cualquier otro caso (estado actual).

Cómo funciona el modo local (pipeline en dos pasos):
    a) YOLOv8 detecta OBJETOS en la foto (letrero, puerta, escalera...).
    b) Un clasificador TF-IDF + RandomForest decide la ZONA a partir de
       la lista de objetos detectados (ej.: "letrero escalera puerta" -> Bloque A).

Todos los modos devuelven el mismo formato, así que las vistas no cambian.
"""
import importlib.util
import random
from functools import lru_cache

from django.conf import settings
from PIL import Image, ImageOps

# Zona que devuelve la simulación. Debe existir en el admin con este nombre.
ZONA_SIMULADA = "Bloque A"

# Rango de confianza que produce la simulación.
CONFIANZA_MINIMA_SIMULADA = 0.65
CONFIANZA_MAXIMA_SIMULADA = 0.98

# Confianza mínima para que YOLO cuente un objeto como detectado.
CONFIANZA_MINIMA_DETECCION = 0.25


# ----------------------------------------------------------------------
# Modo 3: simulación
# ----------------------------------------------------------------------
def reconocer_zona_simulado(foto, cantidad=5):
    """
    Simula el reconocimiento de zona.

    Args:
        foto: Archivo de imagen subido.
        cantidad: Número de detecciones (cajas) simuladas a generar.

    Returns:
        dict con el formato común a todos los modos:
            {
                "zona": "Bloque A",
                "confianza": 0.91,
                "detecciones": [
                    {"clase": "Bloque A", "confianza": 0.91, "caja": [x1, y1, x2, y2]},
                    ...
                ],
                "modo": "simulado",
                "simulado": True,
            }
    """
    with Image.open(foto) as imagen:
        ancho, alto = imagen.size
    foto.seek(0)

    confianza = round(random.uniform(CONFIANZA_MINIMA_SIMULADA, CONFIANZA_MAXIMA_SIMULADA), 2)

    detecciones = []
    for _ in range(cantidad):
        x1 = random.randint(0, ancho // 2)
        y1 = random.randint(0, alto // 2)
        detecciones.append(
            {
                "clase": ZONA_SIMULADA,
                "confianza": round(random.uniform(CONFIANZA_MINIMA_SIMULADA, confianza), 2),
                "caja": [x1, y1, random.randint(x1 + 1, ancho), random.randint(y1 + 1, alto)],
            }
        )
    # La detección principal es la de mayor confianza.
    detecciones.sort(key=lambda deteccion: deteccion["confianza"], reverse=True)
    detecciones[0]["confianza"] = confianza

    return {
        "zona": ZONA_SIMULADA,
        "confianza": confianza,
        "detecciones": detecciones,
        "modo": "simulado",
        "simulado": True,
    }


# ----------------------------------------------------------------------
# Modo 2: modelos locales (YOLOv8 + TF-IDF + RandomForest)
# ----------------------------------------------------------------------
def modelos_locales_disponibles():
    """True si existen los 3 archivos del modelo y las librerías necesarias."""
    archivos = (settings.MODELO_YOLO, settings.MODELO_CLASIFICADOR, settings.MODELO_TFIDF)
    librerias = ("ultralytics", "sklearn", "joblib")
    return all(archivo.exists() for archivo in archivos) and all(
        importlib.util.find_spec(libreria) is not None for libreria in librerias
    )


@lru_cache(maxsize=1)
def cargar_modelos():
    """
    Carga los modelos UNA sola vez (la primera foto tarda más; las
    siguientes reutilizan los modelos ya cargados en memoria).
    """
    import joblib
    from ultralytics import YOLO

    return (
        YOLO(str(settings.MODELO_YOLO)),
        joblib.load(settings.MODELO_CLASIFICADOR),
        joblib.load(settings.MODELO_TFIDF),
    )


def detectar_objetos(imagen):
    """
    Detecta objetos con YOLOv8.

    Args:
        imagen: PIL.Image en RGB.

    Returns:
        Lista de detecciones {"clase", "confianza", "caja"}.
    """
    modelo_yolo, _, _ = cargar_modelos()
    resultado = modelo_yolo(imagen, conf=CONFIANZA_MINIMA_DETECCION, verbose=False)[0]
    return [
        {
            "clase": resultado.names[int(clase)],
            "confianza": round(float(confianza), 2),
            "caja": [round(float(valor)) for valor in caja],
        }
        for clase, confianza, caja in zip(
            resultado.boxes.cls, resultado.boxes.conf, resultado.boxes.xyxy, strict=True
        )
    ]


def predecir_zona(objetos, clasificador, vectorizador):
    """
    Decide la zona a partir de los nombres de los objetos detectados.

    Args:
        objetos: Lista de clases, ej.: ["letrero", "escalera", "puerta"].
        clasificador: RandomForestClassifier entrenado.
        vectorizador: TfidfVectorizer entrenado.

    Returns:
        (nombre_zona, confianza)
    """
    texto = " ".join(objetos)
    probabilidades = clasificador.predict_proba(vectorizador.transform([texto]))[0]
    mejor = int(probabilidades.argmax())
    return str(clasificador.classes_[mejor]), round(float(probabilidades[mejor]), 2)


def reconocer_zona_modelo_local(foto):
    """Reconocimiento real con los modelos entrenados en backend/ml/."""
    with Image.open(foto) as archivo:
        imagen = ImageOps.exif_transpose(archivo).convert("RGB")
    foto.seek(0)

    detecciones = detectar_objetos(imagen)
    if not detecciones:
        # Sin objetos no hay forma de decidir: semáforo rojo.
        return {
            "zona": None,
            "confianza": 0.0,
            "detecciones": [],
            "modo": "local",
            "simulado": False,
        }

    _, clasificador, vectorizador = cargar_modelos()
    zona, confianza = predecir_zona(
        [deteccion["clase"] for deteccion in detecciones], clasificador, vectorizador
    )
    return {
        "zona": zona,
        "confianza": confianza,
        "detecciones": detecciones,
        "modo": "local",
        "simulado": False,
    }


# ----------------------------------------------------------------------
# Modo 1: microservicio externo (pendiente)
# ----------------------------------------------------------------------
def reconocer_zona_ia_service(foto):
    """
    PENDIENTE: enviará la foto por HTTP al microservicio ia_service.

    Respuesta esperada del microservicio (mismo formato que los demás modos):
        {"zona": "Bloque A", "confianza": 0.93,
         "detecciones": [{"clase": ..., "confianza": ..., "caja": [...]}]}

    Implementación sugerida (cuando exista el servicio):
        respuesta = requests.post(settings.IA_SERVICE_URL, files={"foto": foto}, timeout=15)
        datos = respuesta.json()
        datos.update(modo="ia_service", simulado=False)
        return datos
    """
    raise NotImplementedError("El microservicio ia_service todavía no está disponible.")


# ----------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------
def reconocer_zona(foto):
    """Punto de entrada único que usan las vistas."""
    if settings.IA_SERVICE_URL:
        return reconocer_zona_ia_service(foto)
    if modelos_locales_disponibles():
        return reconocer_zona_modelo_local(foto)
    return reconocer_zona_simulado(foto)


def calcular_ruta_simulado(origen, destino):
    """
    Calcula el camino entre una zona de origen y un destino.

    Usa el algoritmo de Dijkstra sobre los pasillos del campus (ver
    rutas/services.py). Es "simulado" porque las coordenadas son
    aproximadas, no medidas en el campus real.

    Returns:
        (waypoints, distancia_en_metros)
    """
    from rutas.services import calcular_camino  # Evita importación circular.

    return calcular_camino(origen, destino)

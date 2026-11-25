"""
ia_service/modelo_onnx.py

Ejecuta el modelo YOLO26 exportado a ONNX (best.onnx) SIN PyTorch ni ultralytics:
solo onnxruntime (CPU) + numpy + Pillow. Así cabe en el servidor de 1 GB.

Formatos de salida que entiende (en píxeles de la imagen 640x640):
    [1, 4 + clases, 8400] -> cx, cy, w, h + un puntaje por clase (0-1). Se elige la
                             clase con más puntaje y se aplica NMS con numpy (IoU 0.7).
                             Es el formato de nuestro best.onnx.
    [1, 300, 6]           -> x1, y1, x2, y2, confianza, clase (ya sin NMS).

El preprocesamiento es el mismo de ultralytics (LetterBox):
    - se reduce la foto manteniendo la proporción hasta caber en 640x640;
    - se centra y se rellena con gris 114;
    - RGB, valores 0-1, formato NCHW float32.
"""
from pathlib import Path

import numpy as np
from PIL import Image

LADO_ENTRADA = 640
GRIS_RELLENO = 114
IOU_NMS = 0.7
MAX_DETECCIONES = 300


def leer_nombres(ruta_yaml):
    """Nombres de las clases desde data.yaml ("names" puede ser lista o diccionario)."""
    import yaml  # pyyaml: liviano, se importa aquí para que las pruebas no lo exijan

    with open(ruta_yaml, encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo) or {}
    nombres = datos.get("names") or []
    if isinstance(nombres, dict):
        return {int(k): str(v) for k, v in nombres.items()}
    return {i: str(n) for i, n in enumerate(nombres)}


def letterbox(imagen, lado=LADO_ENTRADA):
    """
    Foto RGB de Pillow -> (tensor NCHW float32, escala, relleno_x, relleno_y).

    Igual que ultralytics.data.augment.LetterBox (center=True, auto=False).
    """
    ancho, alto = imagen.size
    escala = min(lado / alto, lado / ancho)
    nuevo_ancho, nuevo_alto = round(ancho * escala), round(alto * escala)
    relleno_x = (lado - nuevo_ancho) / 2
    relleno_y = (lado - nuevo_alto) / 2
    izquierda = round(relleno_x - 0.1)
    arriba = round(relleno_y - 0.1)

    if (nuevo_ancho, nuevo_alto) != (ancho, alto):
        imagen = imagen.resize((nuevo_ancho, nuevo_alto), Image.BILINEAR)
    lienzo = Image.new("RGB", (lado, lado), (GRIS_RELLENO,) * 3)
    lienzo.paste(imagen, (izquierda, arriba))

    tensor = np.asarray(lienzo, dtype=np.float32) / 255.0  # alto x ancho x 3 (RGB)
    tensor = np.ascontiguousarray(tensor.transpose(2, 0, 1)[None])  # 1 x 3 x alto x ancho
    return tensor, escala, izquierda, arriba


def nms(cajas, puntajes, iou=IOU_NMS):
    """Índices que sobreviven al NMS (cajas x1, y1, x2, y2), de mayor a menor puntaje."""
    orden = puntajes.argsort()[::-1]
    areas = (cajas[:, 2] - cajas[:, 0]).clip(0) * (cajas[:, 3] - cajas[:, 1]).clip(0)
    quedan = []
    while orden.size and len(quedan) < MAX_DETECCIONES:
        i = orden[0]
        quedan.append(i)
        resto = orden[1:]
        xx1 = np.maximum(cajas[i, 0], cajas[resto, 0])
        yy1 = np.maximum(cajas[i, 1], cajas[resto, 1])
        xx2 = np.minimum(cajas[i, 2], cajas[resto, 2])
        yy2 = np.minimum(cajas[i, 3], cajas[resto, 3])
        interseccion = (xx2 - xx1).clip(0) * (yy2 - yy1).clip(0)
        union = areas[i] + areas[resto] - interseccion
        orden = resto[interseccion / np.maximum(union, 1e-9) <= iou]
    return quedan


def a_filas(salida, confianza_minima):
    """
    Salida del modelo -> filas [x1, y1, x2, y2, confianza, clase] (lienzo 640).

    [1, 4+C, 8400]: se transpone, argmax de clase, filtro de confianza y NMS por clase.
    [1, N, 6]:      ya viene lista.
    """
    datos = np.asarray(salida, dtype=np.float32)
    if datos.ndim == 3 and datos.shape[-1] == 6:
        return datos.reshape(-1, 6)
    datos = datos.reshape(datos.shape[-2], datos.shape[-1]).T  # [8400, 4+C]
    puntajes = datos[:, 4:]
    clases = puntajes.argmax(axis=1)
    confianzas = puntajes[np.arange(len(puntajes)), clases]
    mantener = confianzas >= confianza_minima
    cxcywh, clases, confianzas = datos[mantener, :4], clases[mantener], confianzas[mantener]
    if not len(confianzas):
        return np.zeros((0, 6), dtype=np.float32)
    cajas = np.empty_like(cxcywh)
    cajas[:, 0] = cxcywh[:, 0] - cxcywh[:, 2] / 2
    cajas[:, 1] = cxcywh[:, 1] - cxcywh[:, 3] / 2
    cajas[:, 2] = cxcywh[:, 0] + cxcywh[:, 2] / 2
    cajas[:, 3] = cxcywh[:, 1] + cxcywh[:, 3] / 2
    # NMS por clase (como ultralytics): se separan las clases desplazando sus cajas.
    desplazadas = cajas + (clases[:, None] * 7680.0)
    elegidas = nms(desplazadas, confianzas)
    return np.column_stack([cajas[elegidas], confianzas[elegidas], clases[elegidas]])


def decodificar(salida, escala, izquierda, arriba, ancho, alto, nombres, confianza_minima):
    """
    Salida del modelo -> lista de detecciones en la escala de la foto original:
        [{"clase": "Bloque C", "confianza": 0.91, "caja": [x1, y1, x2, y2]}, ...]
    """
    filas = a_filas(salida, confianza_minima)
    detecciones = []
    for x1, y1, x2, y2, confianza, clase in filas:
        if confianza < confianza_minima:
            continue
        caja = [
            min(max((x1 - izquierda) / escala, 0), ancho),
            min(max((y1 - arriba) / escala, 0), alto),
            min(max((x2 - izquierda) / escala, 0), ancho),
            min(max((y2 - arriba) / escala, 0), alto),
        ]
        indice = int(clase)
        detecciones.append(
            {
                "clase": nombres.get(indice, str(indice)),
                "confianza": round(float(confianza), 3),
                "caja": [round(float(v)) for v in caja],
            }
        )
    detecciones.sort(key=lambda d: d["confianza"], reverse=True)
    return detecciones


class ModeloOnnx:
    """best.onnx + data.yaml cargados una sola vez."""

    motor = "onnx"

    def __init__(self, ruta_onnx, ruta_yaml):
        import onnxruntime as ort

        opciones = ort.SessionOptions()
        opciones.intra_op_num_threads = 1  # servidor pequeño: 1 hilo, menos memoria
        self.sesion = ort.InferenceSession(
            str(ruta_onnx), sess_options=opciones, providers=["CPUExecutionProvider"]
        )
        entrada = self.sesion.get_inputs()[0]
        self.nombre_entrada = entrada.name
        lado = entrada.shape[-1]
        self.lado = lado if isinstance(lado, int) else LADO_ENTRADA
        self.nombres = leer_nombres(ruta_yaml) if Path(ruta_yaml).exists() else {}

    def detectar(self, imagen, confianza_minima):
        tensor, escala, izquierda, arriba = letterbox(imagen, self.lado)
        salida = self.sesion.run(None, {self.nombre_entrada: tensor})[0]
        return decodificar(
            salida, escala, izquierda, arriba, imagen.width, imagen.height,
            self.nombres, confianza_minima,
        )

"""
ia_service/main.py

Microservicio de visión artificial de UNEMI Guide AI (FastAPI + YOLO).

Recibe una foto, la pasa por el modelo entrenado y devuelve lo que detectó.
Django (backend/vision/services.py) decide la zona a partir de esas detecciones.

Elige el modelo solo, en este orden:
    1. models/best.onnx (+ models/data.yaml) -> onnxruntime, SIN PyTorch (liviano).
       Instalar: pip install -r requirements-ligero.txt
    2. models/best.pt                        -> ultralytics + PyTorch (~2 GB).
       Instalar: pip install -r requirements.txt

Arrancar en PowerShell (desde la carpeta ia_service, con el venv activo):
    uvicorn main:app --host 127.0.0.1 --port 8001

Endpoints:
    GET  /health   -> dice si el servicio está vivo y si el modelo está cargado
    POST /predict  -> recibe la foto en el campo "foto"
                      responde {"detecciones": [...], "tiempo_ms": 120, "ancho": 640, "alto": 480}
"""
import io
import os
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

CARPETA = Path(__file__).resolve().parent
MODELOS = CARPETA / "models"

# Configuración (se puede cambiar con variables de entorno).
RUTA_ONNX = Path(os.getenv("MODELO_ONNX", str(MODELOS / "best.onnx")))
RUTA_DATA_YAML = Path(os.getenv("MODELO_DATA_YAML", str(MODELOS / "data.yaml")))
RUTA_PT = Path(os.getenv("MODELO_YOLO", str(MODELOS / "best.pt")))
CONFIANZA_MINIMA = float(os.getenv("CONFIANZA_MINIMA", "0.25"))
TAMANO_MAXIMO_MB = int(os.getenv("TAMANO_MAXIMO_MB", "8"))

app = FastAPI(title="UNEMI Guide AI · ia_service", version="2.0.0")


class ModeloPyTorch:
    """best.pt con ultralytics (respaldo si no hay best.onnx)."""

    motor = "pytorch"

    def __init__(self, ruta):
        from ultralytics import YOLO  # Librería pesada: se importa solo cuando hace falta.

        self.modelo = YOLO(str(ruta))

    def detectar(self, imagen, confianza_minima):
        resultado = self.modelo(imagen, conf=confianza_minima, verbose=False)[0]
        cajas = resultado.boxes
        detecciones = [
            {
                "clase": resultado.names[int(cajas.cls[i])],
                "confianza": round(float(cajas.conf[i]), 3),
                "caja": [round(float(v)) for v in cajas.xyxy[i]],  # [x1, y1, x2, y2]
            }
            for i in range(len(cajas))
        ]
        detecciones.sort(key=lambda d: d["confianza"], reverse=True)
        return detecciones


# El modelo se carga UNA vez y se guarda aquí para reutilizarlo.
modelo_cargado = None


def ruta_del_modelo():
    """El archivo que se usará: best.onnx si existe; si no, best.pt."""
    return RUTA_ONNX if RUTA_ONNX.exists() else RUTA_PT


def obtener_modelo():
    """Devuelve el modelo; lo carga del disco solo la primera vez."""
    global modelo_cargado
    if modelo_cargado is None:
        if RUTA_ONNX.exists():
            from modelo_onnx import ModeloOnnx

            modelo_cargado = ModeloOnnx(RUTA_ONNX, RUTA_DATA_YAML)
        elif RUTA_PT.exists():
            modelo_cargado = ModeloPyTorch(RUTA_PT)
        else:
            raise FileNotFoundError(
                f"No hay modelo en {MODELOS}. Copia best.onnx y data.yaml (o best.pt) ahí."
            )
    return modelo_cargado


@app.get("/health")
def estado():
    """Para comprobar que el servicio responde y si el modelo está listo (lo carga si hace falta)."""
    error = None
    try:
        obtener_modelo()
    except Exception as excepcion:  # noqa: BLE001 - se informa en la respuesta
        error = str(excepcion)
    respuesta = {
        "estado": "ok",
        "modelo": str(ruta_del_modelo()),
        "modelo_disponible": ruta_del_modelo().exists(),
        "modelo_cargado": modelo_cargado is not None,
        "motor": getattr(modelo_cargado, "motor", None),
    }
    if modelo_cargado is not None and hasattr(modelo_cargado, "nombres"):
        respuesta["clases"] = len(modelo_cargado.nombres)
    if error:
        respuesta["error"] = error
    return respuesta


@app.post("/predict")
async def predecir(foto: UploadFile = File(...)):
    """Detecta las zonas en la foto."""
    contenido = await foto.read()

    # 1. Validar tamaño
    if len(contenido) > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"La foto supera {TAMANO_MAXIMO_MB} MB.")

    # 2. Abrir la imagen (exif_transpose endereza fotos giradas del celular)
    try:
        with Image.open(io.BytesIO(contenido)) as archivo:
            imagen = ImageOps.exif_transpose(archivo).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.")

    # 3. Cargar el modelo
    try:
        modelo = obtener_modelo()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error))

    # 4. Detectar y medir el tiempo
    inicio = time.perf_counter()
    detecciones = modelo.detectar(imagen, CONFIANZA_MINIMA)
    tiempo_ms = round((time.perf_counter() - inicio) * 1000)

    return {
        "detecciones": detecciones,
        "tiempo_ms": tiempo_ms,
        "ancho": imagen.width,
        "alto": imagen.height,
    }

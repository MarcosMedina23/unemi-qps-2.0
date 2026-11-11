"""
ia_service/main.py

Microservicio de visión artificial de UNEMI Guide AI (FastAPI + YOLOv8).

Recibe una foto, la pasa por el modelo YOLOv8 entrenado (best.pt) y
devuelve lo que detectó. Django (backend/vision/services.py) decide la
zona a partir de esas detecciones.

Arrancar en PowerShell (desde la carpeta ia_service, con el venv activo):
    uvicorn main:app --host 127.0.0.1 --port 8001

Endpoints:
    GET  /health   -> dice si el servicio está vivo y si el modelo existe
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

# Configuración (se puede cambiar con variables de entorno).
RUTA_MODELO = Path(os.getenv("MODELO_YOLO", str(CARPETA / "models" / "best.pt")))
CONFIANZA_MINIMA = float(os.getenv("CONFIANZA_MINIMA", "0.25"))
TAMANO_MAXIMO_MB = int(os.getenv("TAMANO_MAXIMO_MB", "8"))

app = FastAPI(title="UNEMI Guide AI · ia_service", version="1.0.0")

# El modelo se carga UNA vez y se guarda aquí para reutilizarlo.
modelo_cargado = None


def obtener_modelo():
    """Devuelve el modelo YOLOv8; lo carga del disco solo la primera vez."""
    global modelo_cargado
    if modelo_cargado is None:
        if not RUTA_MODELO.exists():
            raise FileNotFoundError(
                f"No existe el modelo {RUTA_MODELO}. Copia tu best.pt en ia_service/models/."
            )
        from ultralytics import YOLO  # Librería pesada: se importa solo cuando hace falta.

        modelo_cargado = YOLO(str(RUTA_MODELO))
    return modelo_cargado


@app.get("/health")
def estado():
    """Para comprobar que el servicio responde y si el modelo está listo."""
    return {
        "estado": "ok",
        "modelo": str(RUTA_MODELO),
        "modelo_disponible": RUTA_MODELO.exists(),
    }


@app.post("/predict")
async def predecir(foto: UploadFile = File(...)):
    """Detecta objetos en la foto con YOLOv8."""
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
    resultado = modelo(imagen, conf=CONFIANZA_MINIMA, verbose=False)[0]
    tiempo_ms = round((time.perf_counter() - inicio) * 1000)

    # 5. Pasar el resultado de YOLO a una lista de diccionarios
    cajas = resultado.boxes
    detecciones = []
    for i in range(len(cajas)):
        detecciones.append(
            {
                "clase": resultado.names[int(cajas.cls[i])],
                "confianza": round(float(cajas.conf[i]), 3),
                "caja": [round(float(valor)) for valor in cajas.xyxy[i]],  # [x1, y1, x2, y2]
            }
        )
    detecciones.sort(key=lambda d: d["confianza"], reverse=True)

    return {
        "detecciones": detecciones,
        "tiempo_ms": tiempo_ms,
        "ancho": imagen.width,
        "alto": imagen.height,
    }

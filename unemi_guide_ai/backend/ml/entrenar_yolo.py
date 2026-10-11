"""
backend/ml/entrenar_yolo.py

Paso 1 del pipeline: entrena YOLOv8 para detectar OBJETOS del campus
(letreros, puertas, escaleras...) y deja el modelo en ml/models/yolo_zone.pt.

Uso (desde la carpeta backend, con el venv activo y requirements-ml.txt instalado):

    # Entrenar desde cero con dataset/dataset.yaml (100 épocas, imágenes de 640 px)
    python ml/entrenar_yolo.py

    # Ya tienes un best.pt entrenado (por ejemplo en Google Colab): solo instálalo
    python ml/entrenar_yolo.py --copiar "C:/ruta/a/best.pt"
"""
import argparse
import shutil
from pathlib import Path

CARPETA_ML = Path(__file__).resolve().parent
CARPETA_MODELOS = CARPETA_ML / "models"
DESTINO_MODELO = CARPETA_MODELOS / "yolo_zone.pt"


def leer_argumentos():
    parser = argparse.ArgumentParser(description="Entrena o instala el modelo YOLOv8.")
    parser.add_argument("--datos", default=str(CARPETA_ML / "dataset" / "dataset.yaml"))
    parser.add_argument("--epocas", type=int, default=100)
    parser.add_argument("--tamano", type=int, default=640, help="Tamaño de imagen (px).")
    parser.add_argument("--modelo-base", default="yolov8n.pt", help="Modelo preentrenado.")
    parser.add_argument("--copiar", help="Ruta de un best.pt ya entrenado para instalarlo.")
    return parser.parse_args()


def instalar_modelo(origen):
    """Copia el modelo a ml/models/yolo_zone.pt, donde lo busca Django."""
    CARPETA_MODELOS.mkdir(parents=True, exist_ok=True)
    shutil.copy(origen, DESTINO_MODELO)
    print(f"Modelo instalado en: {DESTINO_MODELO}")


def main():
    args = leer_argumentos()

    if args.copiar:
        origen = Path(args.copiar)
        if not origen.exists():
            raise SystemExit(f"No existe el archivo: {origen}")
        instalar_modelo(origen)
        return

    from ultralytics import YOLO  # Se importa aquí: es una librería pesada.

    modelo = YOLO(args.modelo_base)
    modelo.train(
        data=args.datos,
        epochs=args.epocas,
        imgsz=args.tamano,
        project=str(CARPETA_ML / "runs"),
        name="yolo_zone",
        exist_ok=True,
    )
    instalar_modelo(Path(modelo.trainer.save_dir) / "weights" / "best.pt")

    metricas = modelo.val(data=args.datos)
    print(f"mAP50 en validación: {metricas.box.map50:.2%}")


if __name__ == "__main__":
    main()

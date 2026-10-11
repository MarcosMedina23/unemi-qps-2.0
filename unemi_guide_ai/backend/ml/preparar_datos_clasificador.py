"""
backend/ml/preparar_datos_clasificador.py

Paso 2 del pipeline: pasa YOLO por fotos ya clasificadas por zona y genera
el CSV con el que se entrena el clasificador.

Organiza las fotos así (el nombre de la carpeta es el nombre de la zona,
igual al registrado en el admin):

    ml/dataset/zonas/
        Bloque A/            foto1.jpg, foto2.jpg, ...
        Bloque C/            ...
        Biblioteca Central/  ...

Uso (desde la carpeta backend):

    python ml/preparar_datos_clasificador.py

Genera ml/dataset/clasificador.csv con las columnas:
    image_id, objects, zone      (objects = clases detectadas separadas por espacio)
"""
import argparse
import csv
from pathlib import Path

CARPETA_ML = Path(__file__).resolve().parent
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


def leer_argumentos():
    parser = argparse.ArgumentParser(description="Genera el CSV del clasificador.")
    parser.add_argument("--fotos", default=str(CARPETA_ML / "dataset" / "zonas"))
    parser.add_argument("--modelo", default=str(CARPETA_ML / "models" / "yolo_zone.pt"))
    parser.add_argument("--salida", default=str(CARPETA_ML / "dataset" / "clasificador.csv"))
    parser.add_argument("--confianza", type=float, default=0.25)
    return parser.parse_args()


def main():
    args = leer_argumentos()
    carpeta_fotos = Path(args.fotos)
    if not carpeta_fotos.exists():
        raise SystemExit(f"No existe la carpeta de fotos: {carpeta_fotos}")

    from ultralytics import YOLO

    modelo = YOLO(args.modelo)
    filas = []
    for carpeta_zona in sorted(p for p in carpeta_fotos.iterdir() if p.is_dir()):
        for foto in sorted(carpeta_zona.iterdir()):
            if foto.suffix.lower() not in EXTENSIONES:
                continue
            resultado = modelo(str(foto), conf=args.confianza, verbose=False)[0]
            objetos = [resultado.names[int(clase)] for clase in resultado.boxes.cls]
            filas.append(
                {"image_id": foto.name, "objects": " ".join(objetos), "zone": carpeta_zona.name}
            )
        print(f"{carpeta_zona.name}: listo")

    with open(args.salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=["image_id", "objects", "zone"])
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"{len(filas)} fotos procesadas. CSV guardado en: {args.salida}")


if __name__ == "__main__":
    main()

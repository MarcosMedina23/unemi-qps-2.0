"""
backend/ml/entrenar_clasificador.py

Paso 3 del pipeline: entrena el clasificador de zonas TF-IDF + RandomForest
a partir de los objetos que detectó YOLO en cada foto.

Idea: cada foto se convierte en un "texto" con sus objetos
("letrero escalera puerta"). TF-IDF lo convierte en números y el
RandomForest aprende qué combinación de objetos corresponde a cada zona.

Uso (desde la carpeta backend):

    python ml/entrenar_clasificador.py
    python ml/entrenar_clasificador.py --csv ml/dataset/clasificador.csv --arboles 1000

Genera ml/models/zone_classifier.pkl y ml/models/tfidf.pkl.
Muestra la precisión y la compara con la meta del proyecto (>= 65 %).
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

CARPETA_ML = Path(__file__).resolve().parent
CARPETA_MODELOS = CARPETA_ML / "models"
PRECISION_MINIMA = 0.65  # Meta del proyecto


def leer_argumentos():
    parser = argparse.ArgumentParser(description="Entrena el clasificador de zonas.")
    parser.add_argument("--csv", default=str(CARPETA_ML / "dataset" / "clasificador.csv"))
    parser.add_argument("--arboles", type=int, default=1000, help="Árboles del RandomForest.")
    parser.add_argument("--prueba", type=float, default=0.2, help="Porción para evaluar.")
    return parser.parse_args()


def leer_csv(ruta):
    """Devuelve (textos, zonas) ignorando las fotos sin objetos detectados."""
    textos, zonas = [], []
    with open(ruta, encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["objects"].strip():
                textos.append(fila["objects"].strip())
                zonas.append(fila["zone"].strip())
    return textos, zonas


def main():
    args = leer_argumentos()
    if not Path(args.csv).exists():
        raise SystemExit(
            f"No existe el CSV: {args.csv}. Ejecuta antes preparar_datos_clasificador.py"
        )

    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split

    textos, zonas = leer_csv(args.csv)
    print(f"Fotos con objetos: {len(textos)} · Zonas: {dict(Counter(zonas))}")

    def crear_modelo():
        # token_pattern "\S+" respeta nombres de clase como "letrero_unemi".
        vectorizador = TfidfVectorizer(token_pattern=r"\S+", lowercase=True)
        clasificador = RandomForestClassifier(
            n_estimators=args.arboles, class_weight="balanced", random_state=42, n_jobs=-1
        )
        return vectorizador, clasificador

    # 1. Evaluación: se entrena con una parte y se mide con la otra.
    puede_estratificar = min(Counter(zonas).values()) >= 2
    x_entreno, x_prueba, y_entreno, y_prueba = train_test_split(
        textos,
        zonas,
        test_size=args.prueba,
        random_state=42,
        stratify=zonas if puede_estratificar else None,
    )
    vectorizador, clasificador = crear_modelo()
    clasificador.fit(vectorizador.fit_transform(x_entreno), y_entreno)
    predicciones = clasificador.predict(vectorizador.transform(x_prueba))
    precision = accuracy_score(y_prueba, predicciones)

    print(classification_report(y_prueba, predicciones, zero_division=0))
    estado = "CUMPLE" if precision >= PRECISION_MINIMA else "NO CUMPLE"
    print(f"Precisión: {precision:.2%} · Meta {PRECISION_MINIMA:.0%} -> {estado}")

    # 2. Modelo final: se entrena con TODOS los datos y se guarda.
    vectorizador, clasificador = crear_modelo()
    clasificador.fit(vectorizador.fit_transform(textos), zonas)
    CARPETA_MODELOS.mkdir(parents=True, exist_ok=True)
    joblib.dump(clasificador, CARPETA_MODELOS / "zone_classifier.pkl")
    joblib.dump(vectorizador, CARPETA_MODELOS / "tfidf.pkl")
    print(f"Modelos guardados en: {CARPETA_MODELOS}")


if __name__ == "__main__":
    main()

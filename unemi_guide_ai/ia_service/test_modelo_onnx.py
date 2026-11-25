"""
Pruebas del modelo ONNX (sin onnxruntime: solo el pre y posprocesamiento).

Ejecutar desde la carpeta ia_service:
    ..\\venv\\Scripts\\python -m unittest test_modelo_onnx
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from modelo_onnx import decodificar, leer_nombres, letterbox


class LetterboxTests(unittest.TestCase):
    def test_foto_horizontal_se_centra_con_relleno_gris(self):
        imagen = Image.new("RGB", (1280, 960), (255, 0, 0))
        tensor, escala, izquierda, arriba = letterbox(imagen)
        self.assertEqual(tensor.shape, (1, 3, 640, 640))
        self.assertEqual(tensor.dtype, np.float32)
        self.assertAlmostEqual(escala, 0.5)
        self.assertEqual((izquierda, arriba), (0, 80))
        # Relleno de arriba: gris 114; centro: rojo.
        self.assertAlmostEqual(float(tensor[0, 0, 10, 320]), 114 / 255, places=4)
        self.assertAlmostEqual(float(tensor[0, 0, 320, 320]), 1.0, places=4)
        self.assertAlmostEqual(float(tensor[0, 1, 320, 320]), 0.0, places=4)


class DecodificarTests(unittest.TestCase):
    def test_cajas_vuelven_a_la_escala_de_la_foto_y_filtra_confianza(self):
        nombres = {0: "Bloque H", 1: "CRAI"}
        salida = np.zeros((1, 300, 6), dtype=np.float32)
        salida[0, 0] = [100, 180, 300, 380, 0.91, 1]   # en el lienzo 640x640
        salida[0, 1] = [0, 80, 640, 560, 0.40, 0]
        # foto 1280x960 -> escala 0.5, relleno arriba 80
        detecciones = decodificar(salida, 0.5, 0, 80, 1280, 960, nombres, 0.25)
        self.assertEqual(len(detecciones), 2)  # las 298 filas en cero se descartan
        self.assertEqual(detecciones[0]["clase"], "CRAI")
        self.assertEqual(detecciones[0]["confianza"], 0.91)
        self.assertEqual(detecciones[0]["caja"], [200, 200, 600, 600])
        self.assertEqual(detecciones[1]["caja"], [0, 0, 1280, 960])


class SalidaYolo8400Tests(unittest.TestCase):
    def test_argmax_nms_y_escala(self):
        nombres = {0: "Bloque H", 1: "CRAI", 2: "SIM"}
        salida = np.zeros((1, 7, 8400), dtype=np.float32)
        # Dos cajas casi iguales de CRAI (el NMS deja una) y una de SIM.
        salida[0, :, 0] = [200, 280, 200, 200, 0.1, 0.90, 0.05]
        salida[0, :, 1] = [202, 282, 200, 200, 0.1, 0.80, 0.05]
        salida[0, :, 2] = [500, 300, 100, 100, 0.0, 0.1, 0.60]
        salida[0, :, 3] = [100, 100, 50, 50, 0.20, 0.1, 0.0]  # bajo 0.25: fuera
        detecciones = decodificar(salida, 0.5, 0, 80, 1280, 960, nombres, 0.25)
        self.assertEqual([d["clase"] for d in detecciones], ["CRAI", "SIM"])
        self.assertAlmostEqual(detecciones[0]["confianza"], 0.9, places=3)
        self.assertEqual(detecciones[0]["caja"], [200, 200, 600, 600])

    def test_sin_nada_sobre_el_umbral(self):
        salida = np.zeros((1, 7, 8400), dtype=np.float32)
        self.assertEqual(decodificar(salida, 1, 0, 0, 640, 640, {}, 0.25), [])


class NombresTests(unittest.TestCase):
    def test_lee_lista_y_diccionario(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "data.yaml"
            ruta.write_text("names: ['Bloque H', 'CRAI']\nnc: 2\n", encoding="utf-8")
            self.assertEqual(leer_nombres(ruta), {0: "Bloque H", 1: "CRAI"})
            ruta.write_text("names:\n  0: Bloque H\n  1: CRAI\n", encoding="utf-8")
            self.assertEqual(leer_nombres(ruta), {0: "Bloque H", 1: "CRAI"})


if __name__ == "__main__":
    unittest.main()

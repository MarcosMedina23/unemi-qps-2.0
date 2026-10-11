"""
Pruebas de visión: semáforo, geometría y reconocimiento simulado.
Ejecutar: python manage.py test vision
"""
from unittest import mock

from django.test import SimpleTestCase

from zonas.tests import foto_jpeg

from .services import (
    modelos_locales_disponibles,
    predecir_zona,
    reconocer_zona,
    reconocer_zona_simulado,
)
from .utils import a_coordenadas, a_metros_locales, clasificar_confianza, distancia_metros


class SemaforoTests(SimpleTestCase):
    def test_verde_desde_085(self):
        resultado = clasificar_confianza(0.85, "Bloque A")
        self.assertEqual(resultado["semaforo"], "verde")
        self.assertEqual(resultado["mensaje"], "¡Zona reconocida! Estás en: Bloque A.")

    def test_amarillo_entre_065_y_085(self):
        resultado = clasificar_confianza(0.70, "Bloque A")
        self.assertEqual(resultado["semaforo"], "amarillo")
        self.assertTrue(resultado["reconocida"])

    def test_rojo_bajo_065(self):
        resultado = clasificar_confianza(0.64, "Bloque A")
        self.assertEqual(resultado["semaforo"], "rojo")
        self.assertFalse(resultado["reconocida"])
        self.assertEqual(
            resultado["mensaje"], "No pudimos reconocer tu ubicación. Intenta con otra foto."
        )


class GeometriaTests(SimpleTestCase):
    def test_distancia_de_un_milesimo_de_grado(self):
        self.assertAlmostEqual(distancia_metros(0, 0, 0, 0.001), 111.2, delta=0.5)

    def test_ida_y_vuelta_entre_coordenadas_y_metros(self):
        x, z = a_metros_locales(-2.1490, -79.6030, -2.1497, -79.6036)
        self.assertEqual(a_coordenadas(x, z, -2.1497, -79.6036), (-2.149, -79.603))


class ReconocimientoSimuladoTests(SimpleTestCase):
    def test_formato_y_rangos(self):
        resultado = reconocer_zona_simulado(foto_jpeg(), cantidad=3)
        self.assertEqual(resultado["zona"], "Bloque A")
        self.assertTrue(0.65 <= resultado["confianza"] <= 0.98)
        self.assertEqual(len(resultado["detecciones"]), 3)
        self.assertEqual(resultado["detecciones"][0]["confianza"], resultado["confianza"])


class ClasificadorFalso:
    """Imita a un RandomForest entrenado (sin instalar scikit-learn)."""

    classes_ = ["Biblioteca Central", "Bloque A"]

    def predict_proba(self, matriz):
        return [ListaConArgmax([0.2, 0.8])]


class ListaConArgmax(list):
    def argmax(self):
        return self.index(max(self))


class VectorizadorFalso:
    def transform(self, textos):
        self.recibido = textos
        return textos


class ModoLocalTests(SimpleTestCase):
    def test_predecir_zona_une_los_objetos_y_elige_la_mas_probable(self):
        vectorizador = VectorizadorFalso()
        zona, confianza = predecir_zona(["letrero", "puerta"], ClasificadorFalso(), vectorizador)
        self.assertEqual(vectorizador.recibido, ["letrero puerta"])
        self.assertEqual((zona, confianza), ("Bloque A", 0.8))

    def test_sin_modelos_entrenados_usa_la_simulacion(self):
        self.assertFalse(modelos_locales_disponibles())
        self.assertEqual(reconocer_zona(foto_jpeg())["modo"], "simulado")

    def test_con_modelos_entrenados_usa_el_modo_local(self):
        resultado_local = {
            "zona": "Bloque A",
            "confianza": 0.9,
            "detecciones": [],
            "modo": "local",
            "simulado": False,
        }
        with (
            mock.patch("vision.services.modelos_locales_disponibles", return_value=True),
            mock.patch("vision.services.reconocer_zona_modelo_local", return_value=resultado_local),
        ):
            self.assertEqual(reconocer_zona(foto_jpeg())["modo"], "local")

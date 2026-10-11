"""
Pruebas de la API de zonas y destinos.  Ejecutar: python manage.py test zonas
"""
import io
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from usuarios.models import Usuario

from .models import Destino, Zona

CLAVE_PRUEBA = "Clave-Prueba-2026"


def crear_campus_de_prueba():
    """Crea las mismas zonas y destinos de database/seed_data.sql."""
    zonas = {}
    for nombre, descripcion, lat, lng in (
        ("Bloque A", "Facultad de Ciencias e Ingeniería", -2.149700, -79.603600),
        ("Bloque B", "Facultad de Ciencias Sociales", -2.149160, -79.604410),
        ("Bloque C", "Laboratorios de Computación", -2.149026, -79.602925),
        ("Biblioteca Central", "Biblioteca y salas de estudio", -2.148351, -79.603600),
        ("Bloque Administrativo", "Rectorado y Secretaría General", -2.149970, -79.602655),
    ):
        zonas[nombre] = Zona.objects.create(
            nombre=nombre, descripcion=descripcion, latitud=lat, longitud=lng
        )
    destinos = {}
    for nombre, tipo, zona, lat, lng in (
        ("Lab. Computación 3", "laboratorio", "Bloque C", -2.148981, -79.602862),
        ("Sala de lectura", "biblioteca", "Biblioteca Central", -2.148297, -79.603555),
        ("Aula B-204", "aula", "Bloque B", -2.149106, -79.604464),
        ("Secretaría General", "oficina", "Bloque Administrativo", -2.150024, -79.602601),
    ):
        destinos[nombre] = Destino.objects.create(
            nombre=nombre, tipo=tipo, zona=zonas[zona], latitud=lat, longitud=lng
        )
    return zonas, destinos


def crear_estudiante(username="estudiante", carrera="Ingeniería de Software"):
    return Usuario.objects.create_user(username, password=CLAVE_PRUEBA, carrera=carrera)


def foto_jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), "navy").save(buffer, "JPEG")
    return SimpleUploadedFile("foto.jpg", buffer.getvalue(), content_type="image/jpeg")


class ApiZonasTests(TestCase):
    def setUp(self):
        self.zonas, self.destinos = crear_campus_de_prueba()
        self.client.login(username=crear_estudiante().username, password=CLAVE_PRUEBA)

    def test_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/zonas/").status_code, 403)

    def test_lista_y_detalle(self):
        self.assertEqual(len(self.client.get("/api/zonas/").json()), 5)
        detalle = self.client.get(f"/api/zonas/{self.zonas['Bloque A'].id}/").json()
        self.assertEqual(detalle["nombre_completo"], "Bloque A — Facultad de Ciencias e Ingeniería")

    def test_detalle_inexistente_devuelve_detalle_en_espanol(self):
        respuesta = self.client.get("/api/zonas/999/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json(), {"detalle": "No hay datos disponibles."})

    def test_solo_lectura(self):
        self.assertEqual(self.client.post("/api/zonas/", {"nombre": "X"}).status_code, 405)
        url_zona = f"/api/zonas/{self.zonas['Bloque A'].id}/"
        self.assertEqual(self.client.delete(url_zona).status_code, 405)

    def test_filtros_de_destinos(self):
        labs = self.client.get("/api/destinos/?tipo=laboratorio").json()
        self.assertEqual([d["nombre"] for d in labs], ["Lab. Computación 3"])
        busqueda = self.client.get("/api/destinos/?q=lectura").json()
        self.assertEqual(busqueda[0]["nombre"], "Sala de lectura")

    def test_sin_resultados_devuelve_404(self):
        respuesta = self.client.get("/api/destinos/?q=no-existe")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()["detalle"], "No hay datos disponibles.")


class ReconocimientoTests(TestCase):
    def setUp(self):
        self.zonas, _ = crear_campus_de_prueba()
        self.client.login(username=crear_estudiante().username, password=CLAVE_PRUEBA)

    def test_reconoce_bloque_a_con_semaforo(self):
        datos = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()}).json()
        self.assertTrue(datos["reconocida"])
        self.assertIn(datos["semaforo"], {"verde", "amarillo"})
        self.assertEqual(datos["zona"]["nombre"], "Bloque A")
        self.assertTrue(0.65 <= datos["confianza"] <= 0.98)
        self.assertEqual(len(datos["detecciones"]), 5)
        self.assertTrue(datos["simulado"])
        self.assertLess(datos["tiempo_ms"], 5000)  # Meta: reconocer en <= 5 s

    def test_rechaza_archivo_que_no_es_imagen(self):
        archivo = SimpleUploadedFile("x.jpg", b"texto", content_type="image/jpeg")
        respuesta = self.client.post("/api/zonas/reconocer/", {"foto": archivo})
        self.assertEqual(respuesta.status_code, 400)

    def test_zona_no_registrada_devuelve_404(self):
        Zona.objects.filter(nombre="Bloque A").delete()
        respuesta = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()})
        self.assertEqual(respuesta.status_code, 404)

    def test_sin_zona_detectada_devuelve_semaforo_rojo(self):
        sin_objetos = {
            "zona": None,
            "confianza": 0.0,
            "detecciones": [],
            "modo": "local",
            "simulado": False,
        }
        with mock.patch("zonas.views.reconocer_zona", return_value=sin_objetos):
            datos = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()}).json()
        self.assertEqual(datos["semaforo"], "rojo")
        self.assertFalse(datos["reconocida"])
        self.assertIsNone(datos["zona"])

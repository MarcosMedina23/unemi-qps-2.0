"""
Pruebas de rutas: algoritmo de Dijkstra, cálculo por API e historial.
Ejecutar: python manage.py test rutas
"""
from django.core.management import call_command
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase

from zonas.models import Zona
from zonas.tests import CLAVE_PRUEBA, crear_campus_de_prueba, crear_estudiante

from .models import Conexion, Historial, Pasillo, Ruta
from .services import (
    GrafoCampus,
    Nodo,
    RutaNoEncontradaError,
    calcular_camino,
    obtener_pasillos_y_conexiones,
)


class DijkstraTests(SimpleTestCase):
    """Algoritmo puro, sin base de datos."""

    def test_prefiere_desvio_si_es_mas_corto(self):
        grafo = GrafoCampus()
        for clave, x in (("A", 0), ("B", 20), ("C", 40)):
            grafo.agregar_nodo(Nodo(clave, clave, x, 0))
        grafo.conectar("A", "B")
        grafo.conectar("B", "C")
        grafo._vecinos["A"]["C"] = grafo._vecinos["C"]["A"] = 100  # Camino directo más largo
        camino, distancia = grafo.camino_mas_corto("A", "C")
        self.assertEqual([nodo.clave for nodo in camino], ["A", "B", "C"])
        self.assertEqual(distancia, 40)

    def test_sin_conexion_lanza_error(self):
        grafo = GrafoCampus()
        grafo.agregar_nodo(Nodo("A", "A", 0, 0))
        grafo.agregar_nodo(Nodo("B", "B", 10, 0))
        with self.assertRaises(RutaNoEncontradaError):
            grafo.camino_mas_corto("A", "B")


class CalculoCaminoTests(TestCase):
    def setUp(self):
        self.zonas, self.destinos = crear_campus_de_prueba()

    def test_camino_por_la_plaza_central_con_giro(self):
        waypoints, distancia = calcular_camino(
            self.zonas["Bloque A"], self.destinos["Lab. Computación 3"]
        )
        instrucciones = [punto["instruccion"] for punto in waypoints]
        self.assertIn("Plaza Central", instrucciones[1])
        self.assertIn("gira a la derecha", instrucciones[1])
        self.assertEqual(instrucciones[-1], "¡Llegaste a Lab. Computación 3!")
        self.assertAlmostEqual(distancia, 145, delta=5)


class ApiRutasTests(TestCase):
    def setUp(self):
        self.zonas, self.destinos = crear_campus_de_prueba()
        self.ruta = Ruta.objects.create(
            origen=self.zonas["Bloque A"], destino=self.destinos["Lab. Computación 3"]
        )
        self.estudiante = crear_estudiante()
        self.client.login(username=self.estudiante.username, password=CLAVE_PRUEBA)

    def calcular(self, destino):
        return self.client.post(
            "/api/rutas/calcular/",
            {"origen_id": self.zonas["Bloque A"].id, "destino_id": destino.id},
            content_type="application/json",
        )

    def test_calcula_y_completa_el_camino(self):
        datos = self.calcular(self.destinos["Lab. Computación 3"]).json()
        self.assertEqual(datos["destino"]["nombre"], "Lab. Computación 3")
        self.assertEqual(datos["tiempo_minutos"], 2)  # 145 m a 1.4 m/s
        self.assertEqual(len(datos["escena"]["zonas"]), 5)
        self.ruta.refresh_from_db()
        self.assertTrue(self.ruta.camino_json)  # Quedó guardado

    def test_sin_ruta_registrada(self):
        respuesta = self.calcular(self.destinos["Secretaría General"])
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("No encontramos una ruta disponible", respuesta.json()["detalle"])

    def test_guardar_y_listar_historial(self):
        self.assertEqual(self.client.get("/api/historial/").status_code, 404)  # Vacío
        respuesta = self.client.post(
            "/api/historial/", {"ruta_id": self.ruta.id}, content_type="application/json"
        )
        self.assertEqual(respuesta.status_code, 201)
        lista = self.client.get("/api/historial/").json()
        self.assertEqual(lista[0]["ruta"]["destino"]["nombre"], "Lab. Computación 3")

    def test_cada_usuario_ve_solo_su_historial(self):
        ajeno = Historial.objects.create(usuario=crear_estudiante("otro"), ruta=self.ruta)
        self.assertEqual(self.client.get(f"/api/historial/{ajeno.id}/").status_code, 404)

    def test_historial_no_se_puede_editar_ni_borrar(self):
        consulta = Historial.objects.create(usuario=self.estudiante, ruta=self.ruta)
        url = f"/api/historial/{consulta.id}/"
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.put(url, {}, content_type="application/json").status_code, 405)


class PasillosEnAdminTests(TestCase):
    """Los pasillos y conexiones del admin reemplazan a los de mapa_campus.py."""

    def setUp(self):
        self.zonas, self.destinos = crear_campus_de_prueba()

    def test_sin_pasillos_usa_los_de_mapa_campus(self):
        pasillos, conexiones = obtener_pasillos_y_conexiones()
        self.assertEqual([p[0] for p in pasillos], ["P-01", "P-02", "P-03"])
        self.assertEqual(len(conexiones), 2)

    def crear_pasillo(self, codigo, nombre, latitud, longitud):
        return Pasillo.objects.create(
            codigo=codigo, nombre=nombre, latitud=latitud, longitud=longitud
        )

    def test_conexion_calcula_su_distancia(self):
        plaza = self.crear_pasillo("P-01", "Plaza", -2.14916, -79.6036)
        norte = self.crear_pasillo("P-03", "Norte", -2.148756, -79.6036)
        conexion = Conexion.objects.create(pasillo_a=plaza, pasillo_b=norte)
        self.assertAlmostEqual(conexion.distancia_m, 44.9, delta=0.2)

    def test_no_permite_conectar_un_pasillo_consigo_mismo(self):
        plaza = self.crear_pasillo("P-01", "Plaza", -2.14916, -79.6036)
        with self.assertRaises(IntegrityError):
            Conexion.objects.create(pasillo_a=plaza, pasillo_b=plaza, distancia_m=1)

    def test_ruta_pasa_por_el_pasillo_registrado_en_el_admin(self):
        self.crear_pasillo("X-01", "Patio Nuevo", -2.1494, -79.6033)
        laboratorio = self.destinos["Lab. Computación 3"]
        waypoints, _ = calcular_camino(self.zonas["Bloque A"], laboratorio)
        self.assertIn("Patio Nuevo", waypoints[1]["instruccion"])


class FixtureDatosDemoTests(TestCase):
    def test_loaddata_carga_el_campus_y_las_rutas_funcionan(self):
        call_command("loaddata", "datos_demo", verbosity=0)
        self.assertEqual(Zona.objects.count(), 5)
        self.assertEqual(Pasillo.objects.count(), 3)
        self.assertEqual(Ruta.objects.count(), 4)

        estudiante = crear_estudiante()
        self.client.login(username=estudiante.username, password=CLAVE_PRUEBA)
        ruta = Ruta.objects.get(destino__nombre="Lab. Computación 3")
        datos = self.client.post(
            "/api/rutas/calcular/",
            {"origen_id": ruta.origen_id, "destino_id": ruta.destino_id},
            content_type="application/json",
        ).json()
        self.assertAlmostEqual(datos["distancia"], 145, delta=5)

"""
Pruebas de rutas: algoritmo de Dijkstra, cálculo por API e historial.
Ejecutar: python manage.py test rutas
"""
import json
from io import StringIO

import networkx as nx
from django.core.management import call_command
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase

from zonas.models import Zona
from zonas.tests import CLAVE_PRUEBA, crear_campus_de_prueba, crear_estudiante

from .management.commands.cargar_campus import ARCHIVO_CAMPUS
from .models import Conexion, Historial, Pasillo, Ruta
from .services import (
    RutaNoEncontradaError,
    agregar_punto,
    asegurar_camino,
    calcular_camino,
    camino_mas_corto,
    conectar,
    construir_escena,
    obtener_pasillos_y_conexiones,
)


def punto(clave, x):
    """Punto de prueba sobre una línea recta (z = 0)."""
    return {"clave": clave, "nombre": clave, "x": x, "z": 0}


class DijkstraTests(SimpleTestCase):
    """Algoritmo puro, sin base de datos."""

    def test_prefiere_desvio_si_es_mas_corto(self):
        grafo = nx.Graph()
        agregar_punto(grafo, punto("A", 0))
        agregar_punto(grafo, punto("B", 20))
        agregar_punto(grafo, punto("C", 40))
        conectar(grafo, "A", "B")
        conectar(grafo, "B", "C")
        conectar(grafo, "A", "C", distancia=100)  # Camino directo, pero con un gran rodeo
        camino, distancia = camino_mas_corto(grafo, "A", "C")
        self.assertEqual([p["clave"] for p in camino], ["A", "B", "C"])
        self.assertEqual(distancia, 40)

    def test_sin_conexion_lanza_error(self):
        grafo = nx.Graph()
        agregar_punto(grafo, punto("A", 0))
        agregar_punto(grafo, punto("B", 10))
        with self.assertRaises(RutaNoEncontradaError):
            camino_mas_corto(grafo, "A", "B")


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
        self.assertEqual(datos["escena"]["destino"], "Lab. Computación 3")  # Para Unity
        # Para el modo "A tiempo real": el GPS se pasa a metros con este (0, 0)
        referencia = datos["escena"]["referencia"]
        self.assertEqual((referencia["lat"], referencia["lng"]), (-2.1497, -79.6036))
        self.assertGreater(referencia["metros_por_grado"], 111000)
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


class CargarCampusTests(TestCase):
    """python manage.py cargar_campus: el campus real del modelo 3D."""

    def setUp(self):
        call_command("loaddata", "datos_demo", verbosity=0)
        call_command("cargar_campus", stdout=StringIO())

    def test_crea_todos_los_lugares_del_campus(self):
        from zonas.models import Destino

        tipos = set(Destino.objects.values_list("tipo", flat=True))
        for tipo in ["bloque", "edificio", "bano", "deportivo", "estacionamiento", "area_verde", "acceso"]:
            self.assertIn(tipo, tipos)
        self.assertTrue(Destino.objects.filter(nombre="Aula K-301", zona__nombre="Bloque K").exists())
        self.assertTrue(Pasillo.objects.filter(codigo__startswith="C-").exists())
        self.assertFalse(Pasillo.objects.filter(codigo__startswith="P-").exists())  # Los de la demo se van

    def test_se_puede_ejecutar_dos_veces_sin_duplicar(self):
        rutas = Ruta.objects.count()
        call_command("cargar_campus", stdout=StringIO())
        self.assertEqual(Ruta.objects.count(), rutas)

    def test_renombra_el_anexo_del_bloque_h_a_bloque_f_sin_duplicar(self):
        from zonas.models import Destino, Zona

        # Así estaba guardado antes de que el anexo se llamara "Bloque F".
        bloque_f = Zona.objects.get(nombre="Bloque F")
        Zona.objects.filter(pk=bloque_f.pk).update(nombre="Edificio anexo (Bloque H)")
        Destino.objects.filter(nombre="Bloque F").update(nombre="Edificio anexo (Bloque H)")
        rutas = Ruta.objects.count()

        call_command("cargar_campus", stdout=StringIO())

        self.assertFalse(Zona.objects.filter(nombre="Edificio anexo (Bloque H)").exists())
        self.assertEqual(Zona.objects.get(nombre="Bloque F").pk, bloque_f.pk)  # La misma zona
        self.assertEqual(Destino.objects.get(nombre="Bloque F").tipo, "bloque")
        self.assertEqual(Ruta.objects.count(), rutas)  # Conserva sus rutas, no crea otras

    def test_renombra_el_anexo_del_bloque_m_a_bloque_l_sin_duplicar(self):
        from zonas.models import Destino, Zona

        # Así estaba guardado antes de que el anexo se llamara "Bloque L".
        bloque_l = Zona.objects.get(nombre="Bloque L")
        Zona.objects.filter(pk=bloque_l.pk).update(nombre="Edificio anexo (Bloque M)")
        Destino.objects.filter(nombre="Bloque L").update(nombre="Edificio anexo (Bloque M)", tipo="edificio")
        rutas = Ruta.objects.count()

        call_command("cargar_campus", stdout=StringIO())

        self.assertFalse(Zona.objects.filter(nombre="Edificio anexo (Bloque M)").exists())
        self.assertEqual(Zona.objects.get(nombre="Bloque L").pk, bloque_l.pk)  # La misma zona
        self.assertEqual(Destino.objects.get(nombre="Bloque L").tipo, "bloque")
        self.assertEqual(Ruta.objects.count(), rutas)  # Conserva sus rutas, no crea otras

    def test_ruta_por_las_calles_hasta_el_bloque_k(self):
        ruta = Ruta.objects.get(origen__nombre="Entrada peatonal", destino__nombre="Aula K-301")
        asegurar_camino(ruta)
        self.assertGreater(ruta.distancia, 100)
        # Solo giros: nada de "continúa recto" cada 10 m por las calles
        self.assertLess(len(ruta.camino_json), 15)
        # La escena usa las coordenadas del modelo 3D: termina en la puerta del Bloque K
        with open(ARCHIVO_CAMPUS, encoding="utf-8") as archivo:
            puerta_k = next(l for l in json.load(archivo)["lugares"] if l["id"] == "K")
        final = construir_escena(ruta)["camino"][-1]
        self.assertAlmostEqual(final["x"], puerta_k["x"], delta=1)
        self.assertAlmostEqual(final["z"], -puerta_k["z"], delta=1)  # La escena usa z = sur

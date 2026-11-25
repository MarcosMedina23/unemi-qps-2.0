"""
Pruebas de la API de zonas y destinos.  Ejecutar: python manage.py test zonas
"""
import io
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

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


def foto_jpeg(tipo="nitida"):
    """
    Foto de prueba con detalles (ventanas de un "edificio"), para que pase el
    control de calidad. tipo: "nitida", "borrosa", "oscura" o "tapada".
    """
    if tipo == "tapada":
        imagen = Image.new("RGB", (640, 480), "navy")
    else:
        imagen = Image.new("RGB", (640, 480), (150, 170, 200))
        dibujo = ImageDraw.Draw(imagen)
        dibujo.rectangle((80, 120, 560, 470), fill=(200, 190, 170))
        for x in range(100, 540, 40):
            for y in range(140, 450, 50):
                dibujo.rectangle((x, y, x + 25, y + 30), fill=(40, 60, 90))
        if tipo == "borrosa":
            imagen = imagen.filter(ImageFilter.GaussianBlur(6))
        elif tipo == "oscura":
            imagen = ImageEnhance.Brightness(imagen).enhance(0.15)
    buffer = io.BytesIO()
    imagen.save(buffer, "JPEG")
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

    def test_reconoce_zona_registrada_con_semaforo(self):
        datos = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()}).json()
        self.assertTrue(datos["reconocida"])
        self.assertIn(datos["semaforo"], {"verde", "amarillo"})
        # La simulación ubica al estudiante en una zona registrada al azar.
        self.assertIn(datos["zona"]["nombre"], set(Zona.objects.values_list("nombre", flat=True)))
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
        with mock.patch("vision.services.elegir_zona_simulada", return_value="Bloque A"):
            respuesta = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()})
        self.assertEqual(respuesta.status_code, 404)

    def test_bloque_a_se_ubica_en_el_bloque_t_del_campus_real(self):
        # En el campus real (cargar_campus) no hay "Bloque A": es el Bloque T (FACI).
        Zona.objects.filter(nombre="Bloque A").update(nombre="Bloque T (FACI)")
        with mock.patch("vision.services.elegir_zona_simulada", return_value="Bloque A"):
            datos = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()}).json()
        self.assertEqual(datos["zona"]["nombre"], "Bloque T (FACI)")

    def test_clases_de_roboflow_sin_tildes_ni_parentesis(self):
        # Roboflow no acepta tildes ni paréntesis: "Bloque T (FACI)" -> "Bloque T -FACI-".
        Zona.objects.filter(nombre="Bloque A").update(nombre="Bloque T (FACI)")
        with mock.patch("vision.services.elegir_zona_simulada", return_value="Bloque T -FACI-"):
            datos = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()}).json()
        self.assertEqual(datos["zona"]["nombre"], "Bloque T (FACI)")

    def test_clave_nombre_ignora_tildes_signos_y_mayusculas(self):
        from .views import clave_nombre

        self.assertEqual(clave_nombre("Entrada de vehiculos"), clave_nombre("Entrada de vehículos"))
        self.assertEqual(
            clave_nombre("Bloque de Investigacion de Biotecnologia"),
            clave_nombre("Bloque de Investigación de Biotecnología"),
        )
        self.assertNotEqual(clave_nombre("Bloque B"), clave_nombre("Bloque C"))

    def test_sin_zona_detectada_devuelve_semaforo_rojo(self):
        sin_objetos = {
            "zona": None,
            "confianza": 0.0,
            "detecciones": [],
            "modo": "local",
            "simulado": False,
        }
        with mock.patch("zonas.views.reconocer_zona", return_value=sin_objetos):
            respuesta = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()})
        self.assertEqual(respuesta.status_code, 400)
        datos = respuesta.json()
        self.assertEqual(
            datos["detalle"], "No pudimos reconocer tu ubicación, intenta con mejor iluminación."
        )
        self.assertEqual(datos["semaforo"], "rojo")
        self.assertFalse(datos["reconocida"])
        self.assertIsNone(datos["zona"])


class GruposIATests(TestCase):
    """Clases de la IA que agrupan zonas cercanas (zonas/grupos_ia.py)."""

    def setUp(self):
        crear_campus_de_prueba()
        for nombre in ("Bloque V", "Bloque W", "Bloque X", "Bloque H", "Bloque N",
                       "Entrada peatonal", "Canchas"):
            Zona.objects.create(nombre=nombre, latitud=-2.149, longitud=-79.603)
        self.client.login(username=crear_estudiante().username, password=CLAVE_PRUEBA)

    def reconocer(self, clase):
        with mock.patch("vision.services.elegir_zona_simulada", return_value=clase):
            return self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()}).json()

    def test_grupo_devuelve_su_zona_principal(self):
        from .views import buscar_zona

        self.assertEqual(buscar_zona("Bloques V-W-X").nombre, "Bloque W")
        self.assertEqual(buscar_zona("bloques v w x").nombre, "Bloque W")

    def test_clases_viejas_siguen_con_su_propia_zona(self):
        from .views import buscar_zona

        for nombre in ("Bloque V", "Bloque X", "Canchas", "Entrada peatonal"):
            self.assertEqual(buscar_zona(nombre).nombre, nombre)

    def test_reconocer_bloque_h_incluye_entrada_peatonal(self):
        datos = self.reconocer("Bloque H")
        self.assertEqual(datos["zona"]["nombre"], "Bloque H")
        self.assertEqual(datos["grupo"]["clase"], "Bloque H")
        self.assertIn("Entrada peatonal", datos["grupo"]["incluye"])
        # No se pierde ningún campo anterior de la respuesta.
        for campo in ("zona", "confianza", "semaforo", "mensaje", "detecciones",
                      "modo", "simulado", "tiempo_ms"):
            self.assertIn(campo, datos)

    def test_reconocer_bloque_n_muestra_lo_que_hay_cerca(self):
        datos = self.reconocer("Bloque N")
        self.assertEqual(datos["zona"]["nombre"], "Bloque N")
        self.assertEqual(datos["grupo"]["cerca"], ["Baño", "Bar"])
        self.assertEqual(datos["grupo"]["incluye"], [])

    def test_clase_nada_devuelve_semaforo_rojo(self):
        nada = {"zona": "Nada", "confianza": 0.9, "detecciones": [], "modo": "ia_service",
                "simulado": False}
        with mock.patch("zonas.views.reconocer_zona", return_value=nada):
            respuesta = self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg()})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["semaforo"], "rojo")
        self.assertIsNone(respuesta.json()["zona"])

    def test_area_verde_sur_sigue_siendo_zona_del_mapa(self):
        # Ya no es clase de la IA, pero la zona y sus rutas no se borran.
        from .views import buscar_zona

        Zona.objects.create(nombre="Área verde sur", latitud=-2.15, longitud=-79.60)
        self.assertEqual(buscar_zona("Area verde sur").nombre, "Área verde sur")

    def test_zona_sin_grupo_devuelve_grupo_null(self):
        datos = self.reconocer("Bloque B")
        self.assertEqual(datos["zona"]["nombre"], "Bloque B")
        self.assertIsNone(datos["grupo"])


def resultado_ia(*detecciones):
    """Resultado falso de la IA: detecciones (clase, confianza), la primera es la mejor."""
    lista = [{"clase": c, "confianza": p, "caja": [0, 0, 10, 10]} for c, p in detecciones]
    mejor = lista[0] if lista else {"clase": None, "confianza": 0.0}
    return {"zona": mejor["clase"], "confianza": mejor["confianza"], "detecciones": lista,
            "modo": "ia_service", "simulado": False}


class RespuestaInteligenteTests(TestCase):
    """Foto mala, dudas entre zonas, GPS y fuera del campus (zonas/reconocimiento.py)."""

    # Coordenadas de las zonas de prueba.
    EN_ADMINISTRATIVO = {"latitud": -2.149970, "longitud": -79.602655, "precision": 10}
    EN_GUAYAQUIL = {"latitud": -2.170998, "longitud": -79.922359, "precision": 20}

    def setUp(self):
        crear_campus_de_prueba()
        self.client.login(username=crear_estudiante().username, password=CLAVE_PRUEBA)

    def reconocer(self, resultado, foto="nitida", **gps):
        with mock.patch("zonas.views.reconocer_zona", return_value=resultado):
            return self.client.post("/api/zonas/reconocer/", {"foto": foto_jpeg(foto), **gps})

    def nombres(self, datos):
        return [o["zona"]["nombre"] for o in datos["opciones"]]

    def test_calidad_detecta_foto_movida_y_oscura(self):
        from vision.calidad import analizar_calidad

        self.assertEqual(analizar_calidad(foto_jpeg())["nivel"], "buena")
        self.assertEqual(analizar_calidad(foto_jpeg("borrosa"))["problemas"], ["borrosa"])
        self.assertEqual(analizar_calidad(foto_jpeg("oscura"))["problemas"], ["oscura"])

    def test_foto_clara_y_segura_se_reconoce(self):
        respuesta = self.reconocer(resultado_ia(("Bloque B", 0.9)))
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["zona"]["nombre"], "Bloque B")
        self.assertIsNone(datos["motivo"])
        self.assertEqual(datos["calidad"]["nivel"], "buena")

    def test_foto_movida_pide_otra_con_consejo_y_opciones(self):
        respuesta = self.reconocer(resultado_ia(("Bloque B", 0.75)), foto="borrosa")
        self.assertEqual(respuesta.status_code, 400)
        datos = respuesta.json()
        self.assertEqual(datos["motivo"], "foto_mala")
        self.assertEqual(datos["semaforo"], "rojo")
        self.assertIn("movida", datos["calidad"]["consejos"][0])
        self.assertEqual(self.nombres(datos), ["Bloque B"])

    def test_foto_movida_pero_ia_muy_segura_se_reconoce_con_consejo(self):
        respuesta = self.reconocer(resultado_ia(("Bloque B", 0.93)), foto="borrosa")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["calidad"]["problemas"], ["borrosa"])

    def test_dos_bloques_parecidos_pregunta_cual(self):
        respuesta = self.reconocer(resultado_ia(("Bloque B", 0.80), ("Bloque C", 0.76)))
        self.assertEqual(respuesta.status_code, 400)
        datos = respuesta.json()
        self.assertEqual(datos["motivo"], "dudosa")
        self.assertEqual(self.nombres(datos), ["Bloque B", "Bloque C"])
        self.assertEqual(datos["opciones"][0]["confianza"], 0.8)

    def test_confianza_media_dice_cerca_de_y_junto_a(self):
        respuesta = self.reconocer(resultado_ia(("Bloque C", 0.45)))
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["semaforo"], "amarillo")
        self.assertEqual(datos["zona"]["nombre"], "Bloque C")
        self.assertTrue(datos["aproximada"])
        self.assertTrue(datos["mensaje"].startswith("Estás cerca del Bloque C, junto al"))
        self.assertIsNotNone(datos["junto_a"])

    def test_confianza_alta_no_es_aproximada(self):
        datos = self.reconocer(resultado_ia(("Bloque C", 0.9))).json()
        self.assertFalse(datos["aproximada"])
        self.assertIn("Estás en: Bloque C", datos["mensaje"])

    def test_confianza_muy_baja_ofrece_la_zona_probable(self):
        datos = self.reconocer(resultado_ia(("Bloque C", 0.32))).json()
        self.assertEqual(datos["motivo"], "dudosa")
        self.assertEqual(self.nombres(datos), ["Bloque C"])

    def test_foto_borrosa_dice_que_la_tome_quieto(self):
        datos = self.reconocer(resultado_ia(("Bloque B", 0.75)), foto="borrosa").json()
        self.assertEqual(datos["mensaje"],
                         "La foto se ve borrosa, vuelve a tomarla con el celular quieto.")

    def test_foto_oscura_pide_buena_luz(self):
        datos = self.reconocer(resultado_ia(("Bloque B", 0.5)), foto="tapada").json()
        self.assertEqual(datos["motivo"], "foto_mala")
        self.assertEqual(datos["mensaje"], "No se entiende la foto, intenta de nuevo con buena luz.")

    def test_ia_caida_sin_simulacion_avisa_y_no_inventa_zona(self):
        from vision.services import resultado_no_disponible

        respuesta = self.reconocer(resultado_no_disponible())
        self.assertEqual(respuesta.status_code, 400)
        datos = respuesta.json()
        self.assertEqual(datos["motivo"], "ia_no_disponible")
        self.assertEqual(datos["semaforo"], "rojo")
        self.assertIsNone(datos["zona"])
        self.assertFalse(datos["simulado"])
        self.assertIn("no está disponible en este momento", datos["mensaje"])

    def test_fuera_del_campus_por_gps(self):
        respuesta = self.reconocer(resultado_ia(("Bloque B", 0.9)), **self.EN_GUAYAQUIL)
        self.assertEqual(respuesta.status_code, 400)
        datos = respuesta.json()
        self.assertEqual(datos["motivo"], "fuera_del_campus")
        self.assertIn("solo funciona dentro de la universidad", datos["mensaje"])
        self.assertEqual(datos["opciones"], [])

    def test_gps_descarta_zona_que_no_cuadra_y_ofrece_la_cercana(self):
        # La IA dice Bloque B, pero el celular está junto al Bloque Administrativo (~215 m).
        datos = self.reconocer(resultado_ia(("Bloque B", 0.9)), **self.EN_ADMINISTRATIVO).json()
        self.assertEqual(datos["motivo"], "dudosa")
        self.assertEqual(self.nombres(datos)[0], "Bloque Administrativo")
        self.assertEqual(datos["opciones"][0]["distancia_m"], 0)

    def test_sin_deteccion_con_gps_ofrece_lo_que_esta_cerca(self):
        datos = self.reconocer(resultado_ia(), **self.EN_ADMINISTRATIVO).json()
        self.assertEqual(datos["motivo"], "dudosa")
        self.assertIn("cerca", datos["mensaje"])
        self.assertIn("Bloque Administrativo", self.nombres(datos))

    def test_sin_deteccion_ni_gps_explica_que_es_solo_para_el_campus(self):
        datos = self.reconocer(resultado_ia()).json()
        self.assertEqual(datos["motivo"], "sin_deteccion")
        self.assertIn("no parece estar dentro de la UNEMI", datos["mensaje"])
        # Se mantiene el detalle de siempre para los clientes anteriores.
        self.assertEqual(
            datos["detalle"], "No pudimos reconocer tu ubicación, intenta con mejor iluminación."
        )

    def test_gps_coherente_confirma_la_zona(self):
        respuesta = self.reconocer(resultado_ia(("Bloque Administrativo", 0.7)),
                                   **self.EN_ADMINISTRATIVO)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["zona"]["nombre"], "Bloque Administrativo")

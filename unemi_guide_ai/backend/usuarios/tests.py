"""
Pruebas de usuarios: ranking de carreras y datos del usuario actual.
Ejecutar: python manage.py test usuarios
"""
from django.test import TestCase

from zonas.tests import CLAVE_PRUEBA, crear_estudiante

from .models import Usuario


class RankingCarrerasTests(TestCase):
    def test_ordena_por_cantidad_y_calcula_porcentaje(self):
        for indice in range(3):
            crear_estudiante(f"enf{indice}", "Enfermería")
        crear_estudiante("der", "Derecho")
        Usuario.objects.create_user("profe", carrera="Derecho", es_estudiante=False)

        ranking = Usuario.objects.ranking_carreras()
        carreras = [(fila["carrera"], fila["total"]) for fila in ranking]
        self.assertEqual(carreras, [("Enfermería", 3), ("Derecho", 1)])
        self.assertEqual(ranking[0]["porcentaje"], 75.0)

    def test_api_sin_estudiantes_devuelve_404(self):
        admin = Usuario.objects.create_user("admin", password=CLAVE_PRUEBA, es_estudiante=False)
        self.client.login(username=admin.username, password=CLAVE_PRUEBA)
        self.assertEqual(self.client.get("/api/usuarios/carreras/").status_code, 404)


class UsuarioActualTests(TestCase):
    def test_devuelve_datos_sin_contrasena(self):
        estudiante = crear_estudiante()
        self.client.login(username=estudiante.username, password=CLAVE_PRUEBA)
        datos = self.client.get("/api/usuarios/yo/").json()
        self.assertEqual(datos["username"], "estudiante")
        self.assertNotIn("password", datos)

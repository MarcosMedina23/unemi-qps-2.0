"""
Pruebas de la web: página única, login, logout y recuperación de cuenta.
Ejecutar: python manage.py test web
"""
import re

from django.core import mail
from django.test import TestCase, override_settings

from usuarios.models import Usuario
from zonas.tests import CLAVE_PRUEBA, crear_estudiante


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AutenticacionTests(TestCase):
    def setUp(self):
        self.estudiante = crear_estudiante()
        self.estudiante.email = "estudiante@unemi.edu.ec"
        self.estudiante.save()

    def test_inicio_requiere_sesion(self):
        self.assertRedirects(self.client.get("/"), "/login/?next=/")

    def test_login_y_pagina_unica(self):
        datos = {"username": "estudiante", "password": CLAVE_PRUEBA}
        respuesta = self.client.post("/login/", datos)
        self.assertRedirects(respuesta, "/")
        pagina = self.client.get("/")
        self.assertContains(pagina, 'data-pantalla="camara"')
        self.assertContains(pagina, "app.js?v=")
        self.assertIn("csrftoken", pagina.cookies)

    def test_no_existe_registro_publico(self):
        self.assertEqual(self.client.get("/registro/").status_code, 404)
        self.assertNotContains(self.client.get("/login/"), "Crea tu cuenta")

    def test_logout_solo_por_post(self):
        self.client.login(username="estudiante", password=CLAVE_PRUEBA)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/login/", fetch_redirect_response=False)

    def test_recuperar_contrasena_completo(self):
        respuesta = self.client.post("/recuperar/", {"email": "estudiante@unemi.edu.ec"})
        self.assertRedirects(respuesta, "/recuperar/enviado/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "UNEMI Guide AI · Crea tu nueva contraseña")

        enlace = re.search(r"http://testserver(\S+)", mail.outbox[0].body).group(1)
        formulario = self.client.get(enlace, follow=True)
        self.assertContains(formulario, "Crea tu nueva contraseña")
        nueva = "Nueva-Clave-Segura-2026"
        url_formulario = formulario.redirect_chain[-1][0]
        self.client.post(url_formulario, {"new_password1": nueva, "new_password2": nueva})
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.check_password(nueva))

    def test_recuperar_usuario_mismo_mensaje_exista_o_no(self):
        existe = self.client.post("/recuperar-usuario/", {"email": "estudiante@unemi.edu.ec"})
        no_existe = self.client.post("/recuperar-usuario/", {"email": "nadie@unemi.edu.ec"})
        self.assertContains(existe, "Si el correo está registrado")
        self.assertContains(no_existe, "Si el correo está registrado")
        self.assertEqual(len(mail.outbox), 1)  # Solo se envió al correo real
        self.assertIn("estudiante", mail.outbox[0].body)

    def test_estudiante_no_entra_al_admin(self):
        self.client.login(username="estudiante", password=CLAVE_PRUEBA)
        respuesta = self.client.get("/admin/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Usuario.objects.get(username="estudiante").is_staff)

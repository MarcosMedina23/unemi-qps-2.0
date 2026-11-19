"""
Pruebas de la web: página única, login, logout, crear cuenta y recuperación de cuenta.
Ejecutar: python manage.py test web
"""
import re
import smtplib
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
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

    def test_login_tiene_enlace_para_crear_cuenta(self):
        self.assertContains(self.client.get("/login/"), 'href="/registro/"')

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

    def test_recuperar_contrasena_muestra_error_si_el_correo_falla(self):
        # Antes Django ocultaba el error y decía «enviado» aunque no saliera nada
        problema = smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")
        with patch("django.core.mail.EmailMessage.send", side_effect=problema):
            respuesta = self.client.post("/recuperar/", {"email": "estudiante@unemi.edu.ec"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No pudimos enviar el correo")

    def test_recuperar_usuario_muestra_error_si_el_correo_falla(self):
        with patch("django.core.mail.EmailMessage.send", side_effect=OSError("sin internet")):
            respuesta = self.client.post("/recuperar-usuario/", {"email": "estudiante@unemi.edu.ec"})
        self.assertContains(respuesta, "No pudimos enviar el correo")

    @override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_aviso_si_el_correo_solo_sale_en_consola(self):
        self.assertContains(self.client.get("/recuperar/"), "EMAIL_HOST_PASSWORD")

    def test_pagina_trae_panel_de_direcciones_y_modos(self):
        self.client.login(username="estudiante", password=CLAVE_PRUEBA)
        pagina = self.client.get("/")
        self.assertContains(pagina, 'data-modo="referencial"')
        self.assertContains(pagina, 'data-modo="tiempo-real"')
        self.assertContains(pagina, 'id="direcciones-lista"')
        self.assertContains(pagina, "gps.js?v=")

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


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", REGISTRO_DOMINIOS=[])
class RegistroTests(TestCase):
    """Crear cuenta desde la página + activación por correo."""

    CLAVE = "Clave-Segura-2026"

    def setUp(self):
        cache.clear()  # El límite de reenvíos se guarda en la caché

    def datos(self, **cambios):
        datos = {
            "first_name": "Ana",
            "last_name": "Pérez",
            "email": "Ana.Perez@Gmail.com",
            "username": "anaperez",
            "carrera": "Ingeniería de Software",
            "semestre": "3",
            "password1": self.CLAVE,
            "password2": self.CLAVE,
        }
        datos.update(cambios)
        return datos

    def enlace_del_correo(self, indice=0):
        return re.search(r"http://testserver(\S+)", mail.outbox[indice].body).group(1)

    def test_formulario_de_registro(self):
        pagina = self.client.get("/registro/")
        self.assertContains(pagina, "Crear cuenta")
        for campo in ("first_name", "last_name", "email", "username", "carrera", "semestre", "password1"):
            self.assertContains(pagina, f'name="{campo}"')

    def test_crear_cuenta_queda_inactiva_y_envia_enlace(self):
        respuesta = self.client.post("/registro/", self.datos())
        self.assertRedirects(respuesta, "/registro/enviado/")
        usuario = Usuario.objects.get(username="anaperez")
        self.assertFalse(usuario.is_active)
        self.assertTrue(usuario.correo_pendiente)
        self.assertFalse(usuario.is_staff)
        self.assertTrue(usuario.es_estudiante)
        self.assertEqual(usuario.email, "ana.perez@gmail.com")
        self.assertEqual(usuario.semestre, 3)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana.perez@gmail.com"])
        self.assertIn("/activar/", mail.outbox[0].body)
        self.assertContains(self.client.get("/registro/enviado/"), "an*******@gmail.com")
        # Sin activar no puede entrar
        self.assertFalse(self.client.login(username="anaperez", password=self.CLAVE))

    def test_enlace_activa_la_cuenta_una_sola_vez(self):
        self.client.post("/registro/", self.datos())
        enlace = self.enlace_del_correo()
        self.assertContains(self.client.get(enlace), "¡Cuenta activada!")
        usuario = Usuario.objects.get(username="anaperez")
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.correo_pendiente)
        self.assertContains(self.client.get(enlace), "ya está activa")
        respuesta = self.client.post("/login/", {"username": "anaperez", "password": self.CLAVE})
        self.assertRedirects(respuesta, "/")

    def test_enlace_falso_no_activa(self):
        self.client.post("/registro/", self.datos())
        enlace = self.enlace_del_correo()
        falso = enlace.rstrip("/")[:-3] + "xyz/"
        self.assertContains(self.client.get(falso), "Enlace no válido")
        self.assertFalse(Usuario.objects.get(username="anaperez").is_active)

    def test_login_sin_activar_explica_y_reenvia_una_vez(self):
        self.client.post("/registro/", self.datos())
        cache.clear()  # Como si hubieran pasado 5 minutos
        datos = {"username": "anaperez", "password": self.CLAVE}
        primera = self.client.post("/login/", datos)
        self.assertContains(primera, "Te enviamos un enlace nuevo")
        self.assertEqual(len(mail.outbox), 2)
        segunda = self.client.post("/login/", datos)
        self.assertContains(segunda, "aún no está activada")
        self.assertEqual(len(mail.outbox), 2)  # No reenvía en cada intento
        # Con la contraseña equivocada no revela nada
        mala = self.client.post("/login/", {"username": "anaperez", "password": "otra"})
        self.assertNotContains(mala, "activada")

    def test_cuenta_desactivada_por_el_admin_no_se_reactiva(self):
        self.client.post("/registro/", self.datos())
        enlace = self.enlace_del_correo()
        Usuario.objects.filter(username="anaperez").update(correo_pendiente=False)
        self.assertContains(self.client.get(enlace), "Enlace no válido")
        self.assertFalse(Usuario.objects.get(username="anaperez").is_active)

    def test_correo_y_usuario_repetidos(self):
        crear_estudiante().__class__.objects.filter(username="estudiante").update(email="ana.perez@gmail.com")
        respuesta = self.client.post("/registro/", self.datos(username="estudiante"))
        self.assertContains(respuesta, "Ya existe una cuenta con este correo")
        self.assertContains(respuesta, "Ya existe un usuario con este nombre")
        self.assertEqual(len(mail.outbox), 0)

    def test_claves_distintas_y_campos_obligatorios(self):
        respuesta = self.client.post("/registro/", self.datos(password2="Otra-Clave-2026", carrera="", first_name=""))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="anaperez").exists())
        self.assertContains(respuesta, "campo--invalido", count=3)

    @override_settings(REGISTRO_DOMINIOS=["unemi.edu.ec"])
    def test_solo_correos_del_dominio_permitido(self):
        respuesta = self.client.post("/registro/", self.datos())
        self.assertContains(respuesta, "Usa tu correo institucional (@unemi.edu.ec)")
        self.client.post("/registro/", self.datos(email="aperez@unemi.edu.ec"))
        self.assertTrue(Usuario.objects.filter(username="anaperez").exists())

    def test_si_el_correo_falla_no_se_guarda_la_cuenta(self):
        problema = smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")
        with patch("django.core.mail.EmailMessage.send", side_effect=problema):
            respuesta = self.client.post("/registro/", self.datos())
        self.assertContains(respuesta, "No pudimos enviar el correo")
        self.assertFalse(Usuario.objects.filter(username="anaperez").exists())
        # Se puede intentar de nuevo con los mismos datos
        self.assertRedirects(self.client.post("/registro/", self.datos()), "/registro/enviado/")

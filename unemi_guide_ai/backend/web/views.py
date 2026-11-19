"""
Vistas de la app ``web``.

    /                    InicioView                Página única (requiere sesión)
    /login/              LoginView de Django       Plantilla registration/login.html
    /logout/             LogoutView de Django      Solo por POST
    /recuperar/...       Vistas de Django          Recuperar contraseña por correo
    /recuperar-usuario/  RecuperarUsuarioView      Envía el usuario por correo

No existe registro público: las cuentas las crea el administrador.
"""
import logging
import smtplib

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import FormView, TemplateView

from .forms import FormularioRecuperarUsuario

logger = logging.getLogger(__name__)

# Errores posibles al hablar con el servidor de correo (clave mala, sin internet...)
ERRORES_CORREO = (smtplib.SMTPException, OSError)


def correo_configurado():
    """False si los correos solo se imprimen en la consola (falta EMAIL_HOST_PASSWORD)."""
    return not settings.EMAIL_BACKEND.endswith("console.EmailBackend")


def explicar_error_correo(problema):
    """Mensaje para el usuario. Con DEBUG=True se agrega la causa técnica."""
    mensaje = "No pudimos enviar el correo en este momento. Intenta más tarde o avisa al administrador."
    if not settings.DEBUG:
        return mensaje
    if isinstance(problema, smtplib.SMTPAuthenticationError):
        causa = ("el servidor rechazó el usuario o la contraseña de aplicación "
                 "(revisa EMAIL_HOST_USER y EMAIL_HOST_PASSWORD en backend/.env)")
    else:
        causa = f"{type(problema).__name__}: {problema}"
    return f"{mensaje} [Modo desarrollo] Causa: {causa}"


class AvisoCorreoMixin:
    """Agrega a la plantilla si el correo está configurado y la versión de los estáticos."""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["version"] = settings.VERSION_ESTATICOS
        # Solo en desarrollo: avisa que el correo sale en la consola y no llega
        contexto["correo_sin_configurar"] = settings.DEBUG and not correo_configurado()
        return contexto


class RecuperarClaveView(AvisoCorreoMixin, auth_views.PasswordResetView):
    """
    Paso 1 de recuperar contraseña. Si el servidor de correo falla, se
    muestra el error en el formulario en vez de decir «enviado» sin enviar.
    """

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ERRORES_CORREO as problema:
            logger.exception("No se pudo enviar el correo de nueva contraseña")
            form.add_error(None, explicar_error_correo(problema))
            return self.form_invalid(form)

# Build WebGL de Unity (File > Build Settings > WebGL). Ver unity/LEEME.md
CARPETA_UNITY = settings.BASE_DIR / "web" / "static" / "web" / "unity" / "Build"

# Unity puede generar los archivos sin comprimir, con Brotli (.br), Gzip (.gz)
# o con "Decompression Fallback" (.unityweb). Se aceptan todos.
EXTENSIONES_UNITY = ("", ".unityweb", ".br", ".gz")
TIPOS_UNITY = {".js": "application/javascript", ".wasm": "application/wasm", ".data": "application/octet-stream"}


def buscar_build_unity():
    """
    Devuelve las URLs del build WebGL de Unity, o None si no hay build.

    No importa el nombre que se le dio al build (unemi, Build, WebGL...):
    se usa el primer ``*.loader.js`` que exista en la carpeta.
    """
    if not CARPETA_UNITY.is_dir():
        return None
    loaders = sorted(CARPETA_UNITY.glob("*.loader.js"))
    if not loaders:
        return None
    nombre = loaders[0].name[: -len(".loader.js")]

    def archivo(sufijo):
        for extension in EXTENSIONES_UNITY:
            if (CARPETA_UNITY / f"{nombre}{sufijo}{extension}").exists():
                return reverse("unity_archivo", args=[f"{nombre}{sufijo}{extension}"])
        return None

    build = {
        "loader": reverse("unity_archivo", args=[loaders[0].name]),
        "data": archivo(".data"),
        "framework": archivo(".framework.js"),
        "codigo": archivo(".wasm"),
    }
    return build if all(build.values()) else None


def archivo_unity(request, nombre):
    """
    Sirve un archivo del build de Unity con las cabeceras que Unity necesita.

    Si el build salió comprimido (.br / .gz), el navegador solo lo acepta si
    llega con ``Content-Encoding``; el servidor de estáticos de Django no lo
    pone, por eso existe esta vista.
    """
    ruta = (CARPETA_UNITY / nombre).resolve()
    if ruta.parent != CARPETA_UNITY.resolve() or not ruta.is_file():
        raise Http404("Archivo de Unity no encontrado")
    base, codificacion = nombre, None
    if nombre.endswith(".br"):
        base, codificacion = nombre[:-3], "br"
    elif nombre.endswith(".gz"):
        base, codificacion = nombre[:-3], "gzip"
    elif nombre.endswith(".unityweb"):
        base = nombre[: -len(".unityweb")]
    tipo = next((t for ext, t in TIPOS_UNITY.items() if base.endswith(ext)), "application/octet-stream")
    respuesta = FileResponse(open(ruta, "rb"), content_type=tipo)
    if codificacion:
        respuesta["Content-Encoding"] = codificacion
    respuesta["Cache-Control"] = "no-cache"
    return respuesta


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InicioView(LoginRequiredMixin, TemplateView):
    """
    Página única del estudiante.

    ``ensure_csrf_cookie`` garantiza que exista la cookie "csrftoken", que
    api.js necesita para enviar las peticiones POST a la API.
    """

    template_name = "web/index.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["version"] = settings.VERSION_ESTATICOS
        # Si ya se copió el build WebGL de Unity, la página muestra Unity en el
        # recorrido 3D. Si no, dibuja el mismo campus con Three.js.
        contexto["unity"] = buscar_build_unity()
        return contexto


class RecuperarUsuarioView(AvisoCorreoMixin, FormView):
    """
    Recupera el nombre de usuario por correo.

    Siempre muestra el mismo mensaje, exista o no el correo, para no
    revelar qué correos están registrados.
    """

    template_name = "recuperar/usuario.html"
    form_class = FormularioRecuperarUsuario

    def form_valid(self, form):
        try:
            form.enviar_usuario()
        except ERRORES_CORREO as problema:
            logger.exception("No se pudo enviar el correo con el nombre de usuario")
            form.add_error(None, explicar_error_correo(problema))
            return self.form_invalid(form)
        return render(
            self.request,
            self.template_name,
            {"enviado": True, "version": settings.VERSION_ESTATICOS},
        )

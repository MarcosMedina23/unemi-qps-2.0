"""
Vistas de la app ``web``.

    /                    InicioView                Página única (requiere sesión)
    /login/              LoginView de Django       Plantilla registration/login.html
    /logout/             LogoutView de Django      Solo por POST
    /recuperar/...       Vistas de Django          Recuperar contraseña por correo
    /recuperar-usuario/  RecuperarUsuarioView      Envía el usuario por correo

No existe registro público: las cuentas las crea el administrador.
"""
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import FormView, TemplateView

from .forms import FormularioRecuperarUsuario


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
        return contexto


class RecuperarUsuarioView(FormView):
    """
    Recupera el nombre de usuario por correo.

    Siempre muestra el mismo mensaje, exista o no el correo, para no
    revelar qué correos están registrados.
    """

    template_name = "recuperar/usuario.html"
    form_class = FormularioRecuperarUsuario

    def form_valid(self, form):
        form.enviar_usuario()
        return render(
            self.request,
            self.template_name,
            {"enviado": True, "version": settings.VERSION_ESTATICOS},
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["version"] = settings.VERSION_ESTATICOS
        return contexto

"""
Rutas de la app ``web``: página única, login y recuperación de cuenta.

Se usan las vistas de autenticación de Django con plantillas propias.
"""
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import (
    FormularioLogin,
    FormularioNuevaClave,
    FormularioRecuperarClave,
)

# Variable que usan las plantillas de login/recuperación para el ?v= de los CSS/JS.
CONTEXTO_VERSION = {"version": settings.VERSION_ESTATICOS}

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    # --- Sesión ---
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=FormularioLogin,
            redirect_authenticated_user=True,
            extra_context=CONTEXTO_VERSION,
        ),
        name="login",
    ),
    # En Django 5 LogoutView solo acepta POST (más seguro).
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # --- Recuperar contraseña (4 pasos) ---
    path(
        "recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="recuperar/clave_form.html",
            form_class=FormularioRecuperarClave,
            email_template_name="recuperar/clave_email.txt",
            subject_template_name="recuperar/clave_asunto.txt",
            success_url=reverse_lazy("recuperar_enviado"),
            extra_context=CONTEXTO_VERSION,
        ),
        name="recuperar",
    ),
    path(
        "recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="recuperar/clave_enviado.html",
            extra_context=CONTEXTO_VERSION,
        ),
        name="recuperar_enviado",
    ),
    path(
        "recuperar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="recuperar/clave_confirmar.html",
            form_class=FormularioNuevaClave,
            success_url=reverse_lazy("recuperar_completo"),
            extra_context=CONTEXTO_VERSION,
        ),
        name="recuperar_confirmar",
    ),
    path(
        "recuperar/completo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="recuperar/clave_completo.html",
            extra_context=CONTEXTO_VERSION,
        ),
        name="recuperar_completo",
    ),
    # --- Recuperar usuario ---
    path(
        "recuperar-usuario/",
        views.RecuperarUsuarioView.as_view(),
        name="recuperar_usuario",
    ),
]

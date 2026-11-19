"""
Admin de ``usuarios``: aquí el administrador crea o revisa las cuentas de
los estudiantes. Los estudiantes también pueden crearla en /registro/.

Para un estudiante: NO marcar "Staff status" ni asignar permisos.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Gestión de usuarios con los campos académicos del proyecto."""

    list_display = ("username", "email", "es_estudiante", "carrera", "semestre", "is_active")
    list_filter = ("es_estudiante", "carrera", "semestre", "is_active", "correo_pendiente", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "carrera")
    ordering = ("username",)

    # Formulario de edición: se agrega el bloque "Datos académicos".
    fieldsets = UserAdmin.fieldsets + (
        ("Datos académicos", {"fields": ("es_estudiante", "carrera", "semestre", "correo_pendiente")}),
    )

    # Formulario de creación: usuario, contraseña, nombre, correo y carrera
    # en una sola pantalla.
    add_fieldsets = (
        (
            "Cuenta",
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
        (
            "Datos personales",
            {
                "classes": ("wide",),
                "fields": ("first_name", "last_name", "email"),
                "description": "El correo se usa para recuperar la contraseña y el usuario.",
            },
        ),
        (
            "Datos académicos",
            {"classes": ("wide",), "fields": ("es_estudiante", "carrera", "semestre")},
        ),
    )

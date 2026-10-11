"""
Enrutador principal de UNEMI Guide AI.

    /admin/                  Panel del administrador (único lugar de carga)
    /api/zonas/ ...          API de zonas y destinos (zonas/urls.py)
    /api/rutas/ ...          API de rutas e historial (rutas/urls.py)
    /api/usuarios/ ...       API del usuario actual y ranking (usuarios/urls.py)
    /                        Web del estudiante, login y recuperación (web/urls.py)
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# Textos del panel de administración.
admin.site.site_header = "UNEMI Guide AI · Administración"
admin.site.site_title = "UNEMI Guide AI"
admin.site.index_title = "Gestión de zonas, destinos, rutas y usuarios"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("zonas.urls")),
    path("api/", include("rutas.urls")),
    path("api/usuarios/", include("usuarios.urls")),
    path("", include("web.urls")),
]

# En desarrollo, Django sirve las fotos subidas (MEDIA_URL = /media/).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

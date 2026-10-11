"""
Configuración de Django para UNEMI Guide AI.

Los valores sensibles (clave secreta, correo, etc.) se leen del archivo
``backend/.env`` con python-dotenv. Ver ``.env.example`` para la lista
completa de variables.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# ------------------------------------------------------------------
# Rutas base y variables de entorno
# ------------------------------------------------------------------
# BASE_DIR = carpeta "backend/" (donde está manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables de backend/.env (si el archivo existe).
load_dotenv(BASE_DIR / ".env")


def leer_booleano(nombre, por_defecto=False):
    """Interpreta una variable de entorno como True/False ("1", "true", "si")."""
    valor = os.getenv(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes"}


# ------------------------------------------------------------------
# Seguridad
# ------------------------------------------------------------------
# La clave por defecto SOLO sirve para desarrollo. En producción se
# define DJANGO_SECRET_KEY en el archivo .env.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-solo-para-desarrollo-cambiar-antes-de-entregar",
)

DEBUG = leer_booleano("DJANGO_DEBUG", por_defecto=True)

# ALLOWED_HOSTS abierto y CORS abierto SOLO en desarrollo (DEBUG=True).
ALLOWED_HOSTS = ["*"] if DEBUG else os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Permite probar con enlaces públicos temporales:
#   - Túnel de Cloudflare (cloudflared tunnel --url ... / compartir_enlace.bat)
#   - Reenvío de puertos de VS Code (pestaña "Puertos", dominio devtunnels.ms)
CSRF_TRUSTED_ORIGINS = ["https://*.trycloudflare.com", "https://*.devtunnels.ms"]

# ------------------------------------------------------------------
# Aplicaciones
# ------------------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "corsheaders",
    # Propias
    "usuarios",
    "zonas",
    "rutas",
    "vision",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CorsMiddleware debe ir antes de CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        # Las plantillas viven en web/templates/ (APP_DIRS las encuentra).
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------------
# Base de datos (SQLite en desarrollo)
# ------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Se puede cambiar el archivo con SQLITE_PATH en .env (útil para pruebas).
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

# ------------------------------------------------------------------
# Usuarios y autenticación
# ------------------------------------------------------------------
AUTH_USER_MODEL = "usuarios.Usuario"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# El enlace para crear una nueva contraseña vence en 1 hora (en segundos).
PASSWORD_RESET_TIMEOUT = 60 * 60

# ------------------------------------------------------------------
# Django REST Framework: solo usuarios con sesión iniciada
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Solo JSON (sin la interfaz navegable de DRF para los estudiantes).
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ------------------------------------------------------------------
# Correo (recuperar contraseña y usuario)
# ------------------------------------------------------------------
# Con credenciales en .env se usa Gmail SMTP (contraseña de aplicación).
# Sin credenciales, los correos se muestran en la consola de runserver.
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or "UNEMI Guide AI <no-responder@unemi-guide.local>"

# ------------------------------------------------------------------
# Idioma y zona horaria (Ecuador)
# ------------------------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Archivos estáticos y multimedia
# ------------------------------------------------------------------
STATIC_URL = "static/"

# Fotos subidas (imágenes de referencia de zonas y fotos del historial).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Se añade como ?v=... a los CSS/JS para que el navegador no use una
# versión vieja guardada en caché. Cámbiala cuando modifiques el frontend.
VERSION_ESTATICOS = os.getenv("VERSION_ESTATICOS", "1.0.0")

# --- AWS S3 (PENDIENTE: no activar todavía) ------------------------------
# Cuando se use S3 bastará con instalar django-storages y descomentar:
#
# STORAGES = {
#     "default": {"BACKEND": "storages.backends.s3.S3Storage"},
#     "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
# }
# AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
# AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# ------------------------------------------------------------------
# Visión artificial
# ------------------------------------------------------------------
# El reconocimiento elige el modo automáticamente (vision/services.py):
#   1. IA_SERVICE_URL definido      -> microservicio externo ia_service.
#   2. Modelos locales entrenados   -> YOLOv8 + TF-IDF + RandomForest (backend/ml/).
#   3. Ninguno de los anteriores    -> modo simulado.
IA_SERVICE_URL = os.getenv("IA_SERVICE_URL", "")

# Archivos que generan los scripts de backend/ml/ (ver README.md, "Visión artificial real").
CARPETA_MODELOS_ML = BASE_DIR / "ml" / "models"
MODELO_YOLO = CARPETA_MODELOS_ML / "yolo_zone.pt"
MODELO_CLASIFICADOR = CARPETA_MODELOS_ML / "zone_classifier.pkl"
MODELO_TFIDF = CARPETA_MODELOS_ML / "tfidf.pkl"

# Métricas objetivo del proyecto.
PRECISION_MINIMA_MODELO = 0.65
TIEMPO_MAXIMO_RECONOCIMIENTO_S = 5

# Tamaño máximo de las fotos que se suben (en megabytes).
TAMANO_MAXIMO_FOTO_MB = 8

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

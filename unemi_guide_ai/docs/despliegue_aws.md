# Despliegue en AWS (Lightsail)

La app está publicada en un servidor de AWS Lightsail, encendida siempre y con https.

## Estado actual

| Dato | Valor |
|---|---|
| Dirección web | https://44-208-82-176.sslip.io |
| Administración | https://44-208-82-176.sslip.io/admin/ (usuario `admin`) |
| Servidor | Lightsail `unemi-guide` · Ubuntu 24.04 · 1 GB RAM · Virginia (us-east-1) |
| IP fija | `44.208.82.176` |
| Dominio | `44-208-82-176.sslip.io` (gratis, sin cuenta: apunta solo a la IP) |
| Certificado https | Let's Encrypt con certbot (se renueva solo) |
| Carpeta en el servidor | `/home/ubuntu/unemi-qps-2.0/unemi_guide_ai` |
| Entorno virtual | `/home/ubuntu/unemi-qps-2.0/unemi_guide_ai/venv` |
| Servicio de la app | `unemi` (Gunicorn en `127.0.0.1:8000`, 2 workers) |
| Sitio de Nginx | `/etc/nginx/sites-available/unemi` |
| Costo | $7/mes, cubierto por los créditos del plan gratuito de AWS |

> **Plan gratuito de AWS:** dura 6 meses o hasta que se acaben los créditos (lo que pase
> primero). Después AWS cierra la cuenta si no se pasa al plan de pago. Revisar antes de mayo de 2027.

El 3D (Three.js / Unity WebGL) corre en el navegador del estudiante, por eso basta 1 GB.
YOLO no se instala en el servidor: el reconocimiento por foto queda en **modo simulado**.

---

## Actualizar el servidor después de cambiar el código

1. Sube tus cambios a GitHub (`git push origin main`).
2. En Lightsail abre el servidor → **Connect using SSH** y ejecuta:

```bash
cd ~/unemi-qps-2.0/unemi_guide_ai && bash deploy/actualizar.sh
```

El script hace `git pull`, instala dependencias, aplica migraciones, junta los estáticos
(`collectstatic`) y reinicia el servicio `unemi`.

---

## Archivos de despliegue del proyecto

| Archivo | Para qué sirve |
|---|---|
| `deploy/instalar_servidor.sh` | Instala todo en un Ubuntu nuevo con un solo comando |
| `deploy/actualizar.sh` | Pone el servidor al día con lo último de GitHub |
| `backend/config/settings.py` | `STATIC_ROOT`, dominio desde `.env`, https y cookies seguras en producción |
| `backend/requirements.txt` | Incluye `gunicorn` |
| `.gitattributes` | Obliga a guardar los `.sh` con finales de línea de Linux |

### Variables del `.env` en el servidor (`backend/.env`)

```
DJANGO_SECRET_KEY=<clave larga generada en el servidor>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=44-208-82-176.sslip.io
DJANGO_CSRF_TRUSTED_ORIGINS=https://44-208-82-176.sslip.io
DJANGO_HTTPS=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
IA_SERVICE_URL=
```

`DJANGO_HTTPS=True` obliga a usar https y protege las cookies. Ponlo en `False` solo si el
servidor todavía no tiene certificado (si no, la página redirige a un https que no existe).

Para editarlo: `nano ~/unemi-qps-2.0/unemi_guide_ai/backend/.env` y luego `sudo systemctl restart unemi`.

---

## Instalar desde cero en otro servidor

1. **Lightsail → Create instance:** Linux/Unix → OS Only → **Ubuntu 24.04 LTS**, plan **$7 (1 GB)**.
2. **Networking:** *Attach static IP* y en *IPv4 Firewall* agregar **HTTPS (443)**
   (22 y 80 ya vienen abiertos).
3. **Dominio:** el más simple es `IP-CON-GUIONES.sslip.io` (ej. `44-208-82-176.sslip.io`).
   Alternativas: DuckDNS (`duckdns.org`) o un subdominio de la UNEMI.
4. **Connect using SSH** y ejecutar:

```bash
git clone https://github.com/MarcosMedina23/unemi-qps-2.0.git
cd unemi-qps-2.0/unemi_guide_ai
bash deploy/instalar_servidor.sh TU-DOMINIO tu_correo@ejemplo.com
```

5. Crear el administrador:

```bash
cd ~/unemi-qps-2.0/unemi_guide_ai/backend
../venv/bin/python manage.py createsuperuser
```

El script instala Nginx, Certbot, el entorno virtual, crea el `.env` con una clave nueva,
ejecuta `migrate`, `collectstatic` y `cargar_campus`, deja Gunicorn como servicio,
configura Nginx y pide el certificado https. Se puede volver a ejecutar sin romper nada.

---

## Comandos útiles en el servidor

| Para | Comando |
|---|---|
| Ver si la app está encendida | `systemctl status unemi` |
| Ver errores de Django | `sudo journalctl -u unemi -n 50` |
| Reiniciar la app | `sudo systemctl restart unemi` |
| Probar la renovación del certificado | `sudo certbot renew --dry-run` |

## Si algo falla

| Síntoma | Solución |
|---|---|
| `$'\r': command not found` al correr un `.sh` | `sed -i 's/\r$//' deploy/*.sh` |
| Error 502 Bad Gateway | `sudo journalctl -u unemi -n 50` muestra el error de Django |
| Error 403 CSRF al iniciar sesión | El dominio de `DJANGO_CSRF_TRUSTED_ORIGINS` debe ser igual al de la barra del navegador, con `https://` |
| La página no carga / redirige mal | `DJANGO_HTTPS=True` sin certificado: pon `False` o ejecuta certbot |
| Falla certbot | El dominio no apunta a la IP o el puerto 443/80 está cerrado en el firewall de Lightsail |
| No se ven estilos ni 3D | `cd backend && ../venv/bin/python manage.py collectstatic --noinput` |

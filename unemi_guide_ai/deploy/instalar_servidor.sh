#!/usr/bin/env bash
# ==========================================================================
#  UNEMI Guide AI - Instalación en un servidor Ubuntu (AWS Lightsail / EC2)
#
#  Uso (dentro del servidor, desde la carpeta unemi_guide_ai):
#     bash deploy/instalar_servidor.sh TU-DOMINIO.duckdns.org tu_correo@gmail.com
#
#  Hace todo: instala programas, crea el venv, el .env, la base de datos,
#  junta los archivos estáticos, deja Gunicorn como servicio, configura
#  Nginx y pide el certificado https gratis (Let's Encrypt).
#  Se puede volver a ejecutar sin romper nada.
# ==========================================================================
set -euo pipefail

DOMINIO="${1:?Escribe el dominio. Ej: bash deploy/instalar_servidor.sh unemi-guide.duckdns.org correo@gmail.com}"
CORREO="${2:?Escribe tu correo para los avisos del certificado https}"

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # carpeta unemi_guide_ai
BACKEND="$APP_DIR/backend"
VENV="$APP_DIR/venv"
USUARIO="$(whoami)"

echo "==> 1/8 Instalando programas del sistema"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-venv python3-pip nginx certbot python3-certbot-nginx git

echo "==> 2/8 Memoria extra (swap de 1 GB) para que pip no se quede sin RAM"
if ! sudo swapon --show | grep -q /swapfile; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> 3/8 Entorno virtual de Python y dependencias"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$BACKEND/requirements.txt"

echo "==> 4/8 Archivo backend/.env"
if [ ! -f "$BACKEND/.env" ]; then
    CLAVE="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(50))')"
    cat > "$BACKEND/.env" <<EOF
DJANGO_SECRET_KEY=$CLAVE
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMINIO
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMINIO
DJANGO_HTTPS=True

# Correo (recuperar contraseña). Sin contraseña, los correos no se envían.
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Microservicio de IA: vacío = modo simulado
IA_SERVICE_URL=
EOF
    chmod 600 "$BACKEND/.env"
    echo "    .env creado con una clave secreta nueva."
else
    echo "    .env ya existía: no se toca."
fi

echo "==> 5/8 Base de datos, archivos estáticos y campus"
cd "$BACKEND"
mkdir -p media
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput
"$VENV/bin/python" manage.py cargar_campus

echo "==> 6/8 Gunicorn como servicio (arranca solo al reiniciar el servidor)"
sudo tee /etc/systemd/system/unemi.service > /dev/null <<EOF
[Unit]
Description=UNEMI Guide AI (Django + Gunicorn)
After=network.target

[Service]
User=$USUARIO
Group=www-data
WorkingDirectory=$BACKEND
ExecStart=$VENV/bin/gunicorn config.wsgi:application --workers 2 --bind 127.0.0.1:8000 --timeout 60
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable unemi
sudo systemctl restart unemi

echo "==> 7/8 Nginx (recibe las visitas y entrega CSS, JS y 3D)"
# Nginx necesita poder entrar a la carpeta del usuario para leer los estáticos.
chmod o+x "$HOME"
sudo tee /etc/nginx/sites-available/unemi > /dev/null <<'EOF'
server {
    listen 80;
    server_name __DOMINIO__;

    # Fotos de hasta 8 MB (TAMANO_MAXIMO_FOTO_MB) + margen.
    client_max_body_size 10M;

    location /static/ {
        alias __BACKEND__/staticfiles/;
        expires 7d;
    }

    location /media/ {
        alias __BACKEND__/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
EOF
sudo sed -i "s|__DOMINIO__|$DOMINIO|g; s|__BACKEND__|$BACKEND|g" /etc/nginx/sites-available/unemi
sudo ln -sf /etc/nginx/sites-available/unemi /etc/nginx/sites-enabled/unemi
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "==> 8/8 Certificado https gratis (Let's Encrypt)"
if sudo certbot --nginx -d "$DOMINIO" -m "$CORREO" --agree-tos --no-eff-email --redirect --non-interactive; then
    echo ""
    echo "LISTO. Abre https://$DOMINIO"
    echo "Falta crear tu administrador:"
    echo "   cd $BACKEND && $VENV/bin/python manage.py createsuperuser"
else
    echo ""
    echo "No se pudo sacar el certificado. Casi siempre es porque el dominio"
    echo "todavía no apunta a la IP de este servidor (revisa DuckDNS) o porque"
    echo "el puerto 80/443 está cerrado en el firewall de Lightsail."
    echo "Cuando lo arregles, ejecuta solo esto:"
    echo "   sudo certbot --nginx -d $DOMINIO -m $CORREO --agree-tos --redirect"
fi

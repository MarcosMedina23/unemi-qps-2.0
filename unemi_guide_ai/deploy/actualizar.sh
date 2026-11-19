#!/usr/bin/env bash
# ==========================================================================
#  UNEMI Guide AI - Subir los últimos cambios de GitHub al servidor.
#  Uso (dentro del servidor, desde la carpeta unemi_guide_ai):
#     bash deploy/actualizar.sh
# ==========================================================================
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$APP_DIR/backend"
VENV="$APP_DIR/venv"

git -C "$APP_DIR" pull
"$VENV/bin/pip" install -r "$BACKEND/requirements.txt"
cd "$BACKEND"
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput
sudo systemctl restart unemi
echo "Actualizado. Estado del servicio:"
sudo systemctl --no-pager --lines=5 status unemi

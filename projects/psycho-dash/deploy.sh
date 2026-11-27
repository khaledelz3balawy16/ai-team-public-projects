#!/bin/bash
# ═══════════════════════════════════════════════════
# Deploy script for psycho-dash on srv1281908
# Usage: bash deploy.sh
# Port: 8016   Service: gunicorn-psycho-dash.service
# ═══════════════════════════════════════════════════
set -e

APP_DIR="/var/www/psycho-dash"
SERVICE="gunicorn-psycho-dash.service"
VENV="$APP_DIR/venv"

echo "▶ Pulling latest code..."
cd "$APP_DIR"
git pull origin main

echo "▶ Building frontend..."
cd "$APP_DIR/frontend"
npm ci
npm run build
# Output → backend/staticfiles/dist

echo "▶ Installing Python deps..."
cd "$APP_DIR/backend"
"$VENV/bin/pip" install -r requirements.txt --quiet

echo "▶ Running migrations..."
"$VENV/bin/python" manage.py migrate --no-input

echo "▶ Collecting static files..."
"$VENV/bin/python" manage.py collectstatic --no-input

echo "▶ Restarting Gunicorn..."
systemctl restart "$SERVICE"

echo "▶ Restarting OpenLiteSpeed..."
/usr/local/lsws/bin/lswsctrl restart

echo "✅ Deploy complete!"

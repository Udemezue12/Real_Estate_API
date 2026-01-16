#!/bin/sh
set -e

echo "=========================================="
echo "Starting Real Estate Platform"
echo "PORT = ${PORT}"
echo "=========================================="

# Ensure PORT exists (Render injects it)
export PORT=${PORT:-8000}

cd /app/estate_app

# IMPORTANT:
# Do NOT touch Redis here
# Do NOT import Celery here
# Do NOT run migrations that connect to Redis

echo "Launching Supervisor..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf

#!/bin/sh
set -e

echo "=========================================="
echo "Starting container entrypoint..."
echo "=========================================="

# Move to app directory
cd /app/estate_app


echo "Starting Supervisor to manage Uvicorn and Celery..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
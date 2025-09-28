#!/bin/sh
# Exit on error
set -e

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Start Gunicorn with Uvicorn workers (ASGI)
echo "Starting Gunicorn (Uvicorn workers)..."
exec gunicorn -k uvicorn.workers.UvicornWorker digitalcare.asgi:application \
    --bind 0.0.0.0:${PORT:-8000} --workers 4

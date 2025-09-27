#!/bin/sh
# Exit on error
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z "$HOST" "$POSTGRES_PORT"; do
  sleep 1
done
echo "PostgreSQL is up!"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Uvicorn..."
exec gunicorn -k uvicorn.workers.UvicornWorker digitalcare.asgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4


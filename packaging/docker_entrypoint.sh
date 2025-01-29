#!/bin/bash

cd /src

echo "Starting initialization..."

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser and groups..."
python manage.py hi_createsuperuser
python manage.py hi_creategroups

echo "Starting supervisord..."
exec "$@"

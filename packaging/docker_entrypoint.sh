#!/bin/bash

cd /app

python manage.py migrate --noinput
python manage.py hi_createsuperuser
python manage.py hi_creategroups

exec "$@"

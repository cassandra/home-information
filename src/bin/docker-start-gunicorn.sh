#!/bin/sh

NUM_WORKERS=3
NUM_THREADS=3
BINDARG=unix:/var/run/gunicorn.sock

# Make sure static files in the proper place
./manage.py collectstatic --noinput

exec gunicorn hi.wsgi:application \
  --name gunicorn \
  --workers $NUM_WORKERS \
  --threads $NUM_THREADS \
  --bind=$BINDARG \
  --log-file=-

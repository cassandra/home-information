#!/bin/sh

NUM_WORKERS=3
NUM_THREADS=3
BINDARG=unix:/var/run/gunicorn.sock

exec gunicorn hi.wsgi:application \
  --name gunicorn \
  --workers $NUM_WORKERS \
  --threads $NUM_THREADS \
  --bind=$BINDARG \
  --log-file=-


# Assuming an I/O bound app and if have machine CPU all to itself
#NUM_WORKERS=$(( $(nproc) + 1 ))
#
#BINDARG=unix:/var/run/gunicorn.sock
#
#exec gunicorn hi.asgi:application \
#  --name gunicorn \
#  --workers $NUM_WORKERS \
#  --worker-class uvicorn.workers.UvicornWorker \
#  --bind=$BINDARG \
#  --log-file=-

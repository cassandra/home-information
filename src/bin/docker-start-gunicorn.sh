#!/bin/sh

NUM_WORKERS=3
NUM_THREADS=3
BINDARG=unix:/var/run/gunicorn.sock

exec gunicorn hi.wsgi:application \
  -c /src/conf/gunicorn.conf.py \
  --name gunicorn \
  --workers $NUM_WORKERS \
  --threads $NUM_THREADS \
  --bind=$BINDARG \
  --log-file=-

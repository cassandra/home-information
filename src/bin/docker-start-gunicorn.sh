#!/bin/sh

# NUM_WORKERS must remain "1" until refactored for multiple processes to
# share the state of the background managers and monitors. Else too much
# API polling and processes having inconsistent states.

NUM_WORKERS=1
NUM_THREADS=9
BINDARG=unix:/var/run/gunicorn.sock

check_redis() {
    echo "Checking if Redis is ready..."
    
    REDIS_RETRY_LIMIT=10
    REDIS_RETRY_INTERVAL=1
    counter=0

    until redis-cli -h localhost ping | grep -q PONG; do
        echo "Waiting for Redis to be ready... ($counter seconds elapsed)"
        sleep $REDIS_RETRY_INTERVAL
        counter=$((counter+REDIS_RETRY_INTERVAL))
        if [ "$counter" -ge "$REDIS_RETRY_LIMIT" ]; then
            echo ""
            echo "** ERROR ** Redis did not start within $REDIS_RETRY_LIMIT seconds. Exiting."
            echo ""
            exit 1
        fi
    done

    echo "Redis is ready."
}

check_redis

exec gunicorn hi.wsgi:application \
  -c /src/bin/docker-gunicorn.conf.py \
  --name gunicorn \
  --workers $NUM_WORKERS \
  --threads $NUM_THREADS \
  --bind=$BINDARG \
  --log-file=-

#!/bin/sh

if [ $# -lt 1 ] ; then
    echo "Usage: $0 { dev, stage, prod } [bin bind_arg]"
    exit 1
fi

HIENV=$1
shift
NAME="asgi_worker"
HOMEDIR=/home/hiuser
PROJECTDIR=$HOMEDIR/hi
VIRTUALENVDIR=$HOMEDIR/.virtualenvs/hi_$HIENV
DJANGODIR=$PROJECTDIR/src

if [ ! -d $VIRTUALENVDIR ] ; then
    echo "Did not find virtualenv directory: $VIRTUALENVDIR"
    exit 2
fi

echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd $DJANGODIR
. ${VIRTUALENVDIR}/bin/activate
. ${VIRTUALENVDIR}/bin/postactivate

export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Start your Django ASGI worker
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec ${DJANGODIR}/manage.py runworker channels websocket

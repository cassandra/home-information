#!/bin/sh

if [ $# -lt 1 ] ; then
    echo "Usage: $0 { dev, stage, prod } [bin bind_arg]"
    exit 1
fi

HIENV=$1
shift
NAME="daphne"
HOMEDIR=/home/hiuser
PROJECTDIR=$HOMEDIR/hi
VIRTUALENVDIR=$HOMEDIR/.virtualenvs/hi_$HIENV
DJANGODIR=$PROJECTDIR/src
SOCKFILE=$PROJECTDIR/run/daphne.sock
DJANGO_ASGI_MODULE=hi.asgi

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

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# For testing so can connect
if [ "x$1" = 'xbind' ] ; then
  BINDARG=$2
else
  BINDARG=unix:$SOCKFILE
fi

# Start your Daphne
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)

exec ${VIRTUALENVDIR}/bin/daphne \
	-u ${SOCKFILE} \
	--root-path=${VIRTUALENVDIR} \
	--access-log=- \
	 ${DJANGO_ASGI_MODULE}:application

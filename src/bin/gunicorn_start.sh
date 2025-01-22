#!/bin/sh

if [ $# -lt 1 ] ; then
    echo "Usage: $0 { dev, stage, prod } [bin bind_arg]"
    exit 1
fi

HIENV=$1
shift
NAME="gunicorn"
HOMEDIR=/home/hiuser
PROJECTDIR=$HOMEDIR/hi
VIRTUALENVDIR=$HOMEDIR/.virtualenvs/hi_$HIENV
DJANGODIR=$PROJECTDIR/src
SOCKFILE=$PROJECTDIR/run/gunicorn.sock
USER=hiuser
GROUP=hiusers
NUM_WORKERS=3                                     # how many worker processes should Gunicorn spawn
DJANGO_WSGI_MODULE=hi.wsgi

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

# Make sure static files in the proper place
./manage.py collectstatic --noinput

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# For testing so can connect
if [ "x$1" = 'xbind' ] ; then
  BINDARG=$2
else
  BINDARG=unix:$SOCKFILE
fi

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec ${VIRTUALENVDIR}/bin/gunicorn \
     -c gunicorn.conf.py \
     ${DJANGO_WSGI_MODULE}:application \
     --name $NAME \
     --workers $NUM_WORKERS \
     --user=$USER --group=$GROUP \
     --bind=$BINDARG \
     --log-level=debug \
     --log-file=-

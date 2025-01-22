#!/bin/sh

SOCKFILE=/var/run/daphne.sock

exec daphne \
	-u ${SOCKFILE} \
	--access-log=- \
	 hi.asgi:application

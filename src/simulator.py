#!/usr/bin/env python3
import os
import sys
from subprocess import run

# This script wqraps the Django manage,py script but first sets the Django
# settings to the Simulator settings for running the (separate) simulator
# Django application.


def main():
    settings_module = 'hi.settings.simulator'
    os.environ['DJANGO_SETTINGS_MODULE'] = settings_module

    # Ensure manage.py is being used
    manage_py_path = os.path.join( os.path.dirname(__file__), 'manage.py' )
    if not os.path.exists( manage_py_path ):
        print("Error: manage.py not found in the current directory.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print( "Usage: simulator.py <command> [options]" )
        sys.exit(1)

    # Different default port for simulator's "runserver"
    command = sys.argv[1]
    command_args = sys.argv[2:]
    if command == "runserver":
        if not any( arg.isdigit() for arg in command_args ):
            command_args.append( "7411" )

    full_command = [ 'python', manage_py_path, command ] + command_args + [ f'--settings={settings_module}' ]
    result = run( full_command )
    sys.exit( result.returncode )

    
if __name__ == "__main__":
    main()

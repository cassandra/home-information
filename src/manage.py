#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import re
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hi.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    set_default_port_if_needed()  # HI Customization
    execute_from_command_line( sys.argv )

    
def set_default_port_if_needed():
    if ( len(sys.argv) < 2 ) or ( sys.argv[1] != "runserver" ):
        return

    default_port_override = os.environ.get( 'DJANGO_DEV_PORT' )
    if not default_port_override:
        return

    if runserver_has_hostname_only_arg():
        last_arg = sys.argv[-1]
        new_last_arg = f'{last_arg}:{default_port_override}'
        sys.argv[-1] = new_last_arg
        return
    
    if not runserver_has_port_specified():
        sys.argv.append( default_port_override )
        return

    return


def runserver_has_hostname_only_arg():
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return False
    if len(sys.argv) == 2:
        return False

    last_arg = sys.argv[-1]
    if last_arg.startswith( '--' ):
        return False
    if re.fullmatch( r'\d+', last_arg ):
        return False
    if re.fullmatch( r'\d+\.\d+\.\d+\.\d+', last_arg ):
        return True
    if re.fullmatch( r'[a-zA-Z0-9_][a-zA-Z0-9\-_\.]+', last_arg ):
        return True
    return False
    

def runserver_has_port_specified() -> bool:
    """Checks if a port is provided in the runserver command arguments."""
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return False

    for arg in sys.argv[2:]:
        if arg.startswith("--"):
            continue
        if re.fullmatch( r'\d{4,5}', arg ) or re.fullmatch( r'[\d\.]+:\d{4,5}', arg ):
            return True
        continue
    
    return False


if __name__ == '__main__':
    main()

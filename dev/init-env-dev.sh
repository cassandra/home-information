# Source this script (do not execute it) to activate the project venv and
# load development environment variables. Idempotent — safe to source
# multiple times in the same shell.

PROJ_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# Only activate virtual environment if not already active.
# This prevents shell prompt nesting and makes the script idempotent.
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJ_ROOT/venv/bin/activate" ]; then
        . "$PROJ_ROOT/venv/bin/activate"
        echo "✓ Virtual environment activated"
    else
        echo "ERROR: Virtual environment not found at $PROJ_ROOT/venv/bin/activate"
        echo "Please create it first: python3.11 -m venv venv"
        return 1
    fi
else
    echo "✓ Virtual environment already active: $VIRTUAL_ENV"
    echo "  (Hint: run 'deactivate' first if you need to switch environments)"
fi

# Source development environment variables
if [ -f "$PROJ_ROOT/.private/env/development.sh" ]; then
    . "$PROJ_ROOT/.private/env/development.sh"
    echo "✓ Development environment variables loaded"
else
    echo "ERROR: Environment file not found at $PROJ_ROOT/.private/env/development.sh"
    echo "Please create it first: make env-build-dev"
    return 1
fi

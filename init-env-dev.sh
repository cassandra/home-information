# Only activate virtual environment if not already active
# This prevents shell prompt nesting and makes the script idempotent
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        . venv/bin/activate
        echo "✓ Virtual environment activated"
    else
        echo "ERROR: Virtual environment not found at venv/bin/activate"
        echo "Please create it first: python3.11 -m venv venv"
        return 1
    fi
else
    echo "✓ Virtual environment already active: $VIRTUAL_ENV"
    echo "  (Hint: run 'deactivate' first if you need to switch environments)"
fi

# Source development environment variables
if [ -f ".private/env/development.sh" ]; then
    . .private/env/development.sh
    echo "✓ Development environment variables loaded"
else
    echo "ERROR: Environment file not found at .private/env/development.sh"
    echo "Please create it first: make env-build-dev"
    return 1
fi

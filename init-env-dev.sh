# Only activate virtual environment if not already active
# This prevents shell prompt nesting and makes the script idempotent
if [ -z "$VIRTUAL_ENV" ]; then
    . venv/bin/activate
fi
. .private/env/development.sh

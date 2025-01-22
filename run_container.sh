#!/bin/bash

ENV_VAR_FILE=".private/env/stage.sh"
HI_DATA_DIR="/var/hi/data"
EXTERNAL_PORT=8000
BACKGROUND_FLAGS=""

usage() {
    echo "Usage: $0 [-env ENV_VAR_FILE] [-dir HI_DATA_DIR] [-port EXTERNAL_PORT] [-bg]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -env)
            ENV_VAR_FILE="$2"
            shift 2
            ;;
        -dir)
            HI_DATA_DIR="$2"
            shift 2
            ;;
        -port)
            EXTERNAL_PORT="$2"
            shift 2
            ;;
        -bg)
            BACKGROUND_FLAGS="-d"
            shift 1
            ;;
        *)
            usage
            ;;
    esac
done

if [[ ! -f "$ENV_VAR_FILE" ]]; then
    echo "Error: Environment file '$ENV_VAR_FILE' does not exist."
    exit 1
fi

if [[ -d "$HI_DATA_DIR" ]]; then
    if [[ ! -w "$HI_DATA_DIR" ]]; then
        echo "Error: Directory '$HI_DATA_DIR' exists but is not writable."
        exit 1
    fi
else
    echo "Creating directory '$HI_DATA_DIR'..."
    mkdir -p "$HI_DATA_DIR"
    sudo chown -R "$USER:$USER" "$HI_DATA_DIR"
    chmod -R 775 "$HI_DATA_DIR"
fi

if ! docker image inspect hi > /dev/null 2>&1; then
    echo "Error: Docker image 'hi' does not exist. Please build it first."
    exit 1
fi

docker run $BACKGROUND_FLAGS \
       --name hi \
       --env-file "$ENV_VAR_FILE" \
       -v "$HI_DATA_DIR:/data" \
       -p "$EXTERNAL_PORT:8000" hi

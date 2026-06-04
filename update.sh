#!/bin/bash
set -e  # Exit on any error

# Home Information - Update Script
# Updates an existing Home Information installation to the latest version
# Requires: Docker and existing installation

# Configuration
DOCKER_IMAGE="ghcr.io/cassandra/home-information"
DOCKER_TAG="${1:-latest}"  # Allow override for testing (default: latest)
CONTAINER_NAME="hi"
EXTERNAL_PORT="9411"
# Resolve the existing install directory. install.sh uses the hidden ~/.hi by
# default, but falls back to a non-hidden ~/home-information when Docker cannot
# read dot-directories (e.g. snap Docker). Detect by the install's env file
# (what this updater actually needs) rather than a bare directory.
if [[ -f "${HOME}/home-information/env/local.env" ]]; then
    HI_HOME="${HOME}/home-information"
else
    HI_HOME="${HOME}/.hi"
fi
ENV_FILE="${HI_HOME}/env/local.env"
DATABASE_DIR="${HI_HOME}/database"
MEDIA_DIR="${HI_HOME}/media"
COMPOSE_FILE="${HI_HOME}/docker-compose.yml"
HAS_COMPOSE=0  # Set by check_docker_compose; 1 if `docker compose` is available.

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} Home Information Updater${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}• $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
    fi
    
    # Check existing installation
    if [[ ! -f "${ENV_FILE}" ]]; then
        print_error "No existing installation found. Please run install.sh first."
    fi
    
    print_success "Prerequisites verified"
}

# Probe for `docker compose` (v2 plugin). Sets HAS_COMPOSE=1 when present.
check_docker_compose() {
    if docker compose version &> /dev/null; then
        HAS_COMPOSE=1
    else
        HAS_COMPOSE=0
    fi
}

# Update via docker compose. Used when both compose is available AND the
# install.sh-generated compose file exists at ~/.hi/docker-compose.yml.
# `pull` fetches the latest image; `up -d` recreates the container with it.
update_via_compose() {
    print_info "Pulling latest image via docker compose..."
    if ! docker compose -f "${COMPOSE_FILE}" pull; then
        print_error "Failed to pull latest image. Please check your internet connection."
    fi
    print_success "Latest image pulled successfully"

    print_info "Recreating container..."
    if ! docker compose -f "${COMPOSE_FILE}" up -d; then
        print_error "docker compose up -d failed."
    fi
    print_success "Container recreated"
}

# Pull latest Docker image
pull_latest_image() {
    print_info "Pulling latest Docker image..."
    
    if docker pull "${DOCKER_IMAGE}:${DOCKER_TAG}"; then
        print_success "Latest image pulled successfully"
    else
        print_error "Failed to pull latest image. Please check your internet connection."
    fi
}

# Stop and remove old container
stop_old_container() {
    if docker ps --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Stopping current container..."
        docker stop "${CONTAINER_NAME}"
        print_success "Container stopped"
    fi
    
    if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Removing old container..."
        docker rm "${CONTAINER_NAME}"
        print_success "Old container removed"
    fi
}

# Start new container with latest image
start_new_container() {
    print_info "Starting updated container..."
    
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        --env-file "${ENV_FILE}" \
        -v "${DATABASE_DIR}:/data/database" \
        -v "${MEDIA_DIR}:/data/media" \
        -p "${EXTERNAL_PORT}:8000" \
        "${DOCKER_IMAGE}:${DOCKER_TAG}"
    
    print_success "Updated container started"
}

# Wait for application to be ready
wait_for_app() {
    print_info "Waiting for application to start..."
    
    # Wait up to 30 seconds for the app to be ready
    for i in {1..30}; do
        if curl -s "http://localhost:${EXTERNAL_PORT}" > /dev/null 2>&1; then
            print_success "Application is ready!"
            return 0
        fi
        sleep 1
    done
    
    print_warning "Application may still be starting. Check 'docker logs hi' for details."
}

# Display success message
show_success() {
    echo
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN} Update Complete!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo
    echo -e "${BLUE}🌐 Access your updated Home Information system:${NC}"
    echo -e "   ${BLUE}http://localhost:${EXTERNAL_PORT}${NC}"
    echo
    echo -e "${BLUE}📊 Status check:${NC}"
    echo -e "   View logs: docker logs hi"
    echo -e "   Container status: docker ps"
    echo
    echo -e "${GREEN}Your data and settings have been preserved.${NC}"
    echo
}

# Main update function
main() {
    print_header

    check_prerequisites
    check_docker_compose

    # Use the compose path only when both compose is available AND the
    # install.sh-generated compose file exists. A pre-Phase-2 install has no
    # compose file even on a host where compose is installed; those users
    # continue managing via the legacy `docker run` recreation flow.
    if (( HAS_COMPOSE == 1 )) && [[ -f "${COMPOSE_FILE}" ]]; then
        update_via_compose
    else
        pull_latest_image
        stop_old_container
        start_new_container
    fi

    wait_for_app
    show_success
}

# Run main function
main "$@"
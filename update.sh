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
HI_HOME="${HOME}/.hi"
ENV_FILE="${HI_HOME}/env/local.env"
DATABASE_DIR="${HI_HOME}/database"
MEDIA_DIR="${HI_HOME}/media"

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
    pull_latest_image
    stop_old_container
    start_new_container
    wait_for_app
    show_success
}

# Run main function
main "$@"
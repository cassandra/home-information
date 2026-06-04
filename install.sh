#!/bin/bash
set -e  # Exit on any error

# Home Information - Single Command Installer
# Installs and runs Home Information with minimal user interaction
# Requires: Docker

# Configuration
DOCKER_IMAGE="ghcr.io/cassandra/home-information"  # GitHub Container Registry
DOCKER_TAG="${1:-latest}"  # Allow override for testing (default: latest)
CONTAINER_NAME="hi"
EXTERNAL_PORT="9411"
# Install directory. Defaults to the hidden ~/.hi. choose_install_dir() may
# switch this to the non-hidden HI_HOME_VISIBLE at install time when Docker
# cannot read files inside dot-directories (e.g. snap-packaged Docker, whose
# confinement denies access to hidden home dirs). Derived paths are computed
# from the final HI_HOME by set_install_paths().
HI_HOME="${HOME}/.hi"
HI_HOME_VISIBLE="${HOME}/home-information"
HAS_COMPOSE=0  # Set by check_docker_compose; 1 if `docker compose` is available.

# Derive all install paths from the (possibly updated) HI_HOME.
set_install_paths() {
    ENV_DIR="${HI_HOME}/env"
    DATABASE_DIR="${HI_HOME}/database"
    MEDIA_DIR="${HI_HOME}/media"
    ENV_FILE="${ENV_DIR}/local.env"
    COMPOSE_FILE="${HI_HOME}/docker-compose.yml"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} Home Information Installer${NC}"
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

# Check if Docker is installed and running
check_docker() {
    print_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
    fi
    
    print_success "Docker is installed and running"
}

# Probe for `docker compose` (v2 plugin). Sets HAS_COMPOSE=1 when present.
# Detection only; we do not offer to install the plugin — users without compose
# stay on the legacy `docker run` path. The compose file is still written either
# way so it is available the moment compose is installed.
check_docker_compose() {
    print_info "Checking for docker compose..."

    if docker compose version &> /dev/null; then
        HAS_COMPOSE=1
        print_success "docker compose detected"
    else
        HAS_COMPOSE=0
        print_info "docker compose not detected — will use legacy docker run flow"
    fi
}

# Choose the install directory. Snap-packaged (and otherwise AppArmor-confined)
# Docker cannot read files inside hidden "dot" directories, so it cannot parse a
# compose file or --env-file under ~/.hi and fails with an opaque "permission
# denied". Rather than fingerprint snap (brittle, and misses other confinement),
# we probe the real capability: ask Docker to read a throwaway compose file from
# a dot-directory. If that read is denied, fall back to a non-hidden directory.
#
# `docker compose config` only parses/reads the file (no image pull, no
# container, no network), so the probe is fast and side-effect-free. It needs
# the compose plugin; confined Docker (snap) always bundles it. Without the
# plugin we are on an old, unconfined daemon where the hidden default is fine.
choose_install_dir() {
    if (( HAS_COMPOSE == 0 )); then
        return
    fi

    local probe_dir="${HOME}/.hi-install-probe.$$"
    local probe_file="${probe_dir}/docker-compose.yml"
    mkdir -p "${probe_dir}"
    printf 'services:\n  probe:\n    image: busybox\n    command: ["true"]\n' > "${probe_file}"

    if ! docker compose -f "${probe_file}" config &> /dev/null; then
        HI_HOME="${HI_HOME_VISIBLE}"
        print_info "Docker cannot read hidden directories (e.g. snap Docker);"
        print_info "using ${HI_HOME} instead of ${HOME}/.hi"
    fi

    rm -rf "${probe_dir}"
}

# Check if Python3 is installed (needed for secure secret generation)
check_python() {
    print_info "Checking Python 3 installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.6+ is required but not installed. Please install Python 3.6 or later."
    fi
    
    print_success "Python 3 is installed"
}

# Generate cryptographically secure Django secret key.
# Charset excludes characters that can confuse docker compose's env_file parser
# (quotes, backslash, dollar, hash, equals, backtick) so the generated value
# round-trips cleanly through both docker run --env-file and compose env_file.
generate_secret_key() {
    python3 -c "
import secrets
import string
chars = string.ascii_letters + string.digits + '!@%^&*()-_+[]{}<>?,./:;|~'
print(''.join(secrets.choice(chars) for _ in range(50)))
"
}

# Generate memorable admin password
generate_admin_password() {
    python3 -c "
import secrets
words = [
    'apple', 'banana', 'cherry', 'delta', 'eagle', 'falcon', 'grape', 
    'hunter', 'island', 'joker', 'kitten', 'lemon', 'melon', 'ninja', 'ocean',
    'piano', 'queen', 'robot', 'stone', 'tiger', 'unity', 'voice', 'water',
    'xenon', 'yacht', 'zebra', 'anchor', 'bridge', 'camera', 'dream', 'energy'
]
chosen_words = [secrets.choice(words) for _ in range(3)]
random_number = str(secrets.randbelow(1000))
chosen_words.append(random_number)
print('-'.join(chosen_words))
"
}

# Create required directories
create_directories() {
    print_info "Creating directories..."
    
    # Create directories with proper permissions
    mkdir -p "${ENV_DIR}"
    mkdir -p "${DATABASE_DIR}"
    mkdir -p "${MEDIA_DIR}"
    
    # Secure the env directory (user only)
    chmod 700 "${ENV_DIR}"
    
    print_success "Directories created: ${HI_HOME}"
}

# Generate environment file
create_env_file() {
    print_info "Generating configuration and secrets..."
    
    # Check if env file already exists
    if [[ -f "${ENV_FILE}" ]]; then
        print_warning "Configuration file already exists: ${ENV_FILE}"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Installation cancelled. Remove ${ENV_FILE} to start fresh."
        fi
        
        # Create backup (using portable date format)
        TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
        BACKUP_FILE="${ENV_FILE}.BAK.${TIMESTAMP}"
        cp "${ENV_FILE}" "${BACKUP_FILE}"
        print_info "Backup created: ${BACKUP_FILE}"
    fi
    
    # Generate secrets
    DJANGO_SECRET_KEY=$(generate_secret_key)
    DJANGO_ADMIN_PASSWORD=$(generate_admin_password)
    
    # Create environment file.
    # The unique heredoc terminator INSTALL_ENV_FILE_EOF lets `--list-env-vars`
    # extract the variable names from this exact block without ambiguity.
    cat > "${ENV_FILE}" << INSTALL_ENV_FILE_EOF
# Home Information Environment Configuration
# Generated by install.sh on $(date)

# Core Django Settings
DJANGO_SETTINGS_MODULE=hi.settings.local
DJANGO_SERVER_PORT=8000
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}

# Admin User (for Django admin interface)
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=${DJANGO_ADMIN_PASSWORD}

# Data Paths (inside Docker container)
HI_DB_PATH=/data/database
HI_MEDIA_PATH=/data/media

# Redis Configuration
HI_REDIS_HOST=127.0.0.1
HI_REDIS_PORT=6379
HI_REDIS_KEY_PREFIX=

# Authentication (disabled for simple setup)
HI_SUPPRESS_AUTHENTICATION=true

# Email Settings (disabled for simple setup)
HI_EMAIL_SUBJECT_PREFIX=
HI_DEFAULT_FROM_EMAIL=
HI_SERVER_EMAIL=
HI_EMAIL_HOST=
HI_EMAIL_PORT=587
HI_EMAIL_HOST_USER=
HI_EMAIL_HOST_PASSWORD=
HI_EMAIL_USE_TLS=false
HI_EMAIL_USE_SSL=false

# Network Configuration (for localhost only)
HI_EXTRA_HOST_URLS=
HI_EXTRA_CSP_URLS=
INSTALL_ENV_FILE_EOF
    
    # Secure the env file
    chmod 600 "${ENV_FILE}"
    
    print_success "Configuration file created: ${ENV_FILE}"
    
    # Store admin password for display later
    ADMIN_PASSWORD="${DJANGO_ADMIN_PASSWORD}"
}

# Write a fully-resolved docker-compose.yml to ${HI_HOME}/. Always written, even
# when compose is not available, so it is ready for use the moment the user
# installs the compose plugin. Container name `hi` matches the legacy
# `docker run --name hi` invocation so management commands like `docker logs
# hi`, `docker stop hi`, and `docker start hi` work identically across both
# code paths. No `healthcheck:` stanza — the Dockerfile already defines one,
# and a compose-level stanza would override it.
create_compose_file() {
    print_info "Writing ${COMPOSE_FILE}..."

    # Back up any hand-edited compose file (e.g. reverse-proxy labels, custom
    # networks) before regenerating. Same pattern as create_env_file.
    if [[ -f "${COMPOSE_FILE}" ]]; then
        local timestamp
        timestamp=$(date "+%Y%m%d_%H%M%S")
        local backup_file="${COMPOSE_FILE}.BAK.${timestamp}"
        cp "${COMPOSE_FILE}" "${backup_file}"
        print_info "Existing compose file backed up: ${backup_file}"
    fi

    cat > "${COMPOSE_FILE}" << INSTALL_COMPOSE_FILE_EOF
# Home Information — generated by install.sh
#
# This file is the live config for managing your installation. To use it:
#   cd ${HI_HOME}
#   docker compose ps          # status
#   docker compose logs -f     # follow logs
#   docker compose restart     # restart
#   docker compose down        # stop
#
# Updates: re-run install.sh's companion update.sh script (it detects this
# file and uses compose). Or run \`docker compose pull && docker compose up -d\`
# from ${HI_HOME}.
#
# Re-running install.sh will overwrite this file with regenerated values.

services:
  ${CONTAINER_NAME}:
    image: ${DOCKER_IMAGE}:${DOCKER_TAG}
    container_name: ${CONTAINER_NAME}
    restart: unless-stopped
    ports:
      - "${EXTERNAL_PORT}:8000"
    env_file:
      - ${ENV_FILE}
    volumes:
      - ${DATABASE_DIR}:/data/database
      - ${MEDIA_DIR}:/data/media
INSTALL_COMPOSE_FILE_EOF

    chmod 600 "${COMPOSE_FILE}"
    print_success "Compose file written: ${COMPOSE_FILE}"
}

# Pull Docker image
pull_docker_image() {
    print_info "Pulling Home Information Docker image..."
    
    if docker pull "${DOCKER_IMAGE}:${DOCKER_TAG}"; then
        print_success "Docker image pulled successfully"
    else
        print_error "Failed to pull Docker image. Please check your internet connection."
    fi
}

# Stop any existing container
stop_existing_container() {
    if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Stopping existing container..."
        docker stop "${CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${CONTAINER_NAME}" 2>/dev/null || true
        print_success "Existing container removed"
    fi
}

# Start the container. Branches on HAS_COMPOSE: compose users get compose-managed
# containers; everyone else gets the original `docker run` invocation. Both
# paths produce a container named `hi`, so post-install management commands
# documented in show_success() work identically.
start_container() {
    print_info "Starting Home Information container..."

    if (( HAS_COMPOSE == 1 )); then
        docker compose -f "${COMPOSE_FILE}" up -d
    else
        docker run -d \
            --name "${CONTAINER_NAME}" \
            --restart unless-stopped \
            --env-file "${ENV_FILE}" \
            -v "${DATABASE_DIR}:/data/database" \
            -v "${MEDIA_DIR}:/data/media" \
            -p "${EXTERNAL_PORT}:8000" \
            "${DOCKER_IMAGE}:${DOCKER_TAG}"
    fi

    print_success "Container started successfully"
}

# Wait for application to be ready
wait_for_app() {
    print_info "Waiting for application to start (this may take a minute)..."
    
    # Wait up to 60 seconds for the app to be ready
    for i in {1..60}; do
        if curl -s "http://localhost:${EXTERNAL_PORT}" > /dev/null 2>&1; then
            print_success "Application is ready!"
            return 0
        fi
        sleep 1
        if [ $((i % 10)) -eq 0 ]; then
            print_info "Still waiting... (${i}s)"
        fi
    done
    
    print_warning "Application may still be starting. Check docker logs hi for details."
}

# Display success message
show_success() {
    echo
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN} Installation Complete!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo
    echo -e "${BLUE}🌐 Access your Home Information system:${NC}"
    echo -e "   ${BLUE}http://localhost:${EXTERNAL_PORT}${NC}"
    echo
    echo -e "${BLUE}🔐 Admin credentials:${NC}"
    echo -e "   Email: admin@example.com"
    echo -e "   Password: ${ADMIN_PASSWORD}"
    echo
    echo -e "${BLUE}📁 Your data is stored in:${NC}"
    echo -e "   Database: ${DATABASE_DIR}"
    echo -e "   Uploads: ${MEDIA_DIR}"
    echo
    echo -e "${BLUE}🔧 Useful commands:${NC}"
    echo -e "   View logs: docker logs hi"
    echo -e "   Stop: docker stop hi"
    echo -e "   Start: docker start hi"
    echo -e "   Restart: docker restart hi"
    echo -e "   Update: curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/master/update.sh | bash"
    echo
    echo -e "${GREEN}IMPORTANT: Save your admin credentials securely!${NC}"
    echo
}

# Print the sorted, unique set of env var names this script writes.
# Used by deploy/env-drift-check.sh to detect drift between install.sh,
# deploy/env-generate.py, and local.env.example without running any
# installation steps. Extracts names from the heredoc body itself so the
# listing cannot drift from what the script actually generates.
list_env_vars() {
    local self="${BASH_SOURCE[0]}"
    if [[ ! -f "${self}" ]]; then
        echo "Error: cannot locate install.sh source for --list-env-vars" >&2
        exit 1
    fi
    sed -n '/<< INSTALL_ENV_FILE_EOF$/,/^INSTALL_ENV_FILE_EOF$/p' "${self}" \
        | grep -E '^[A-Z][A-Z0-9_]+=' \
        | sed 's/=.*//' \
        | sort -u
}

# Main installation function
main() {
    print_header

    check_docker
    check_docker_compose
    choose_install_dir
    set_install_paths
    check_python
    create_directories
    create_env_file
    create_compose_file
    pull_docker_image
    stop_existing_container
    start_container
    wait_for_app
    show_success
}

# CLI dispatch: --list-env-vars is a non-installing introspection mode.
if [[ "${1:-}" == "--list-env-vars" ]]; then
    list_env_vars
    exit 0
fi

# Run main function
main "$@"
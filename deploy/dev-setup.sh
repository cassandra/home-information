#!/bin/bash

# Home Information Development Setup Script
# 
# This script automates the development environment setup for new developers.
# It handles git configuration, environment setup, virtual environment creation,
# package installation, and database initialization.
#
# Usage: ./deploy/dev-setup.sh
#
# The script is idempotent and can be run multiple times safely.

set -e  # Exit on error

# Color output functions (matching env-generate.py style)
print_debug() {
    echo "[DEBUG] $1"
}

print_notice() {
    echo ""
    echo "[NOTICE] $1"
    echo ""
}

print_warning() {
    echo ""
    echo -e "\033[96m[WARNING]\033[0m $1"
    echo ""
}

print_error() {
    echo ""
    echo -e "\033[91m[ERROR]\033[0m $1"
    echo ""
}

print_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

print_important() {
    local message="$1"
    local width=80
    local border=$(printf '%*s' "$width" | tr ' ' ' ')
    
    echo ""
    echo -e "\033[7m${border}\033[0m"
    echo "$message" | while IFS= read -r line; do
        printf "\033[7m%-${width}s\033[0m\n" "$line"
    done
    echo -e "\033[7m${border}\033[0m"
    echo ""
}

# Function to prompt for yes/no
prompt_yes_no() {
    local message="$1"
    local default="$2"
    local prompt
    
    if [[ "$default" == "y" ]]; then
        prompt="[Y/n]"
    elif [[ "$default" == "n" ]]; then
        prompt="[y/N]"
    else
        prompt="[y/n]"
    fi
    
    while true; do
        read -p "$message $prompt: " answer
        answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
        
        if [[ -z "$answer" && -n "$default" ]]; then
            answer="$default"
        fi
        
        if [[ "$answer" == "y" || "$answer" == "yes" ]]; then
            return 0
        elif [[ "$answer" == "n" || "$answer" == "no" ]]; then
            return 1
        else
            print_warning "Please answer 'y' or 'n'"
        fi
    done
}

# Function to prompt for string input
prompt_string() {
    local message="$1"
    local default="$2"
    local prompt=""
    
    if [[ -n "$default" ]]; then
        prompt=" [$default]"
    fi
    
    read -p "$message$prompt: " value
    
    if [[ -z "$value" && -n "$default" ]]; then
        value="$default"
    fi
    
    echo "$value"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup script starts here
print_important "Home Information Development Setup

This script will help you set up your development environment.
It will guide you through:
- Git configuration
- Environment variable setup
- Python virtual environment creation
- Package installation
- Database initialization

The script is safe to run multiple times."

# Step 1: Pre-flight checks
print_notice "Step 1: Pre-flight Checks"

# Check if we're in the project root
if [[ ! -f "HI_VERSION" || ! -d "deploy" || ! -d "docs" ]]; then
    print_error "This script must be run from the project root directory."
    print_notice "Please cd to the home-information directory and try again."
    exit 1
fi
print_success "Running from correct directory"

# Check Python 3.11
if command_exists python3.11; then
    print_success "Python 3.11 found"
    PYTHON_CMD="python3.11"
elif command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ "$PYTHON_VERSION" == 3.11* ]]; then
        print_success "Python 3.11 found"
        PYTHON_CMD="python3"
    else
        print_warning "Python 3.11 not found (found $PYTHON_VERSION instead)"
        print_notice "Python 3.11 is recommended. You may experience issues with other versions."
        if ! prompt_yes_no "Continue anyway?" "n"; then
            exit 1
        fi
        PYTHON_CMD="python3"
    fi
else
    print_error "Python 3 not found. Please install Python 3.11 and try again."
    exit 1
fi

# Check git
if ! command_exists git; then
    print_error "Git is not installed. Please install git and try again."
    exit 1
fi
print_success "Git found"

# Check Redis (warning only)
if ! command_exists redis-server && ! command_exists redis-cli; then
    print_warning "Redis not found. You'll need Redis to run the application."
    print_notice "You can install Redis later and continue with the setup now."
    if ! prompt_yes_no "Continue without Redis?" "y"; then
        print_notice "Please install Redis and run this script again."
        exit 1
    fi
else
    print_success "Redis found"
fi

# Check make
if ! command_exists make; then
    print_error "Make is not installed. Please install make and try again."
    exit 1
fi
print_success "Make found"

# Step 2: Git Configuration
print_notice "Step 2: Git Configuration"

# Check if git user is configured
GIT_USER_NAME=$(git config --global user.name || echo "")
GIT_USER_EMAIL=$(git config --global user.email || echo "")

if [[ -z "$GIT_USER_NAME" ]]; then
    print_notice "Git user name not configured"
    GIT_USER_NAME=$(prompt_string "Enter your full name")
    git config --global user.name "$GIT_USER_NAME"
    print_success "Git user name configured"
else
    print_success "Git user name already configured: $GIT_USER_NAME"
fi

if [[ -z "$GIT_USER_EMAIL" ]]; then
    print_notice "Git user email not configured"
    GIT_USER_EMAIL=$(prompt_string "Enter your email address")
    git config --global user.email "$GIT_USER_EMAIL"
    print_success "Git user email configured"
else
    print_success "Git user email already configured: $GIT_USER_EMAIL"
fi

# Check remote configuration
CURRENT_ORIGIN=$(git remote get-url origin 2>/dev/null || echo "")
CURRENT_UPSTREAM=$(git remote get-url upstream 2>/dev/null || echo "")

if [[ -z "$CURRENT_ORIGIN" ]]; then
    print_warning "No 'origin' remote configured"
    print_notice "This should point to your fork of the repository"
    GITHUB_USERNAME=$(prompt_string "Enter your GitHub username")
    
    if prompt_yes_no "Do you have SSH keys set up with GitHub?" "n"; then
        git remote add origin "git@github.com:${GITHUB_USERNAME}/home-information.git"
    else
        git remote add origin "https://github.com/${GITHUB_USERNAME}/home-information.git"
    fi
    print_success "Origin remote configured"
else
    print_success "Origin remote already configured"
fi

if [[ -z "$CURRENT_UPSTREAM" ]]; then
    print_notice "Adding upstream remote"
    git remote add upstream https://github.com/cassandra/home-information.git
    print_success "Upstream remote configured"
else
    print_success "Upstream remote already configured"
fi

# Verify remotes
print_notice "Git remotes configured:"
git remote -v

# Step 3: Environment Setup
print_notice "Step 3: Environment Setup"

# Check if environment file exists
ENV_FILE=".private/env/development.sh"
if [[ ! -f "$ENV_FILE" ]]; then
    print_notice "Environment file not found. Creating it now..."
    make env-build-dev
    print_success "Environment file created"
else
    print_success "Environment file already exists"
    if prompt_yes_no "Do you want to regenerate the environment file?" "n"; then
        make env-build-dev
        print_success "Environment file regenerated"
    fi
fi

# Step 4: Python Virtual Environment
print_notice "Step 4: Python Virtual Environment"

if [[ ! -d "venv" ]]; then
    print_notice "Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
print_notice "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Source environment variables
print_notice "Loading environment variables..."
source "$ENV_FILE"
print_success "Environment variables loaded"

# Step 5: Install Python Packages
print_notice "Step 5: Installing Python Packages"

print_notice "Installing development requirements..."
pip install --quiet --upgrade pip
pip install --quiet -r src/hi/requirements/development.txt
print_success "Python packages installed"

# Step 6: Database Initialization
print_notice "Step 6: Database Initialization"

cd src

# Run Django check
print_notice "Running Django system check..."
if ./manage.py check; then
    print_success "Django system check passed"
else
    print_error "Django system check failed"
    exit 1
fi

# Run migrations
print_notice "Running database migrations..."
./manage.py migrate
print_success "Database migrations completed"

# Create superuser
if ./manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
    print_success "Superuser already exists"
else
    print_notice "Creating superuser..."
    ./manage.py hi_createsuperuser
    print_success "Superuser created"
fi

# Create groups
print_notice "Creating user groups..."
./manage.py hi_creategroups
print_success "User groups created"

# Step 7: Run Tests
print_notice "Step 7: Validation"

if prompt_yes_no "Run unit tests to validate installation?" "y"; then
    print_notice "Running unit tests..."
    if ./manage.py test; then
        print_success "All tests passed!"
    else
        print_warning "Some tests failed. This might be expected if you haven't set up all services yet."
    fi
else
    print_notice "Skipping unit tests"
fi

cd ..

# Final Summary
print_important "Setup Complete!

Your development environment is now configured.

Django Admin Credentials:
- Check $ENV_FILE for credentials
- URL: http://127.0.0.1:8411/admin/

Next Steps:
1. Start Redis server (if installed):
   redis-server

2. In a new terminal, activate the environment:
   . ./init-env-dev.sh

3. Start the development server:
   cd src
   ./manage.py runserver

4. Visit http://127.0.0.1:8411

For daily development, just run:
   . ./init-env-dev.sh

Happy coding!"

# Extract and display admin credentials if available
if [[ -f "$ENV_FILE" ]]; then
    ADMIN_EMAIL=$(grep "DJANGO_SUPERUSER_EMAIL" "$ENV_FILE" | cut -d'"' -f2)
    ADMIN_PASSWORD=$(grep "DJANGO_SUPERUSER_PASSWORD" "$ENV_FILE" | cut -d'"' -f2)
    
    if [[ -n "$ADMIN_EMAIL" && -n "$ADMIN_PASSWORD" ]]; then
        print_important "Admin Credentials:
Email: $ADMIN_EMAIL
Password: $ADMIN_PASSWORD

Please save these credentials securely!"
    fi
fi
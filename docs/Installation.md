<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Installation Guide

Complete installation instructions for Home Information, from quick setup to advanced deployment.

## Prerequisites

- **Docker** - installed and running ([Get Docker](https://docs.docker.com/get-docker/))
- **Python 3.6+** - for secure credential generation (usually pre-installed)

## Quick Installation

**One command gets you running in 30 seconds:**

```shell
curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/master/install.sh | bash
```

**What it does:**
- Verifies Docker is running
- Creates data directories in `~/.hi/`
- Generates secure admin credentials
- Downloads and starts the application
- Shows your login URL and credentials

**Result:** Visit [http://localhost:9411](http://localhost:9411) and sign in with the displayed credentials.

**Data location:**
- Database: `~/.hi/database/`
- Files: `~/.hi/media/`

### Updates

```shell
curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/master/update.sh | bash
```

This preserves all your data while updating to the latest version.

### Environment Variable Changes

If you used the one-liner `install.sh` script and need to change your environment variables, you'll need to re-run in docker to pick up the changes.  The install script runs docker with this command:
```
docker run -d \
       --name "${CONTAINER_NAME}" \
       --restart unless-stopped \
       --env-file "${ENV_FILE}" \
       -v "${DATABASE_DIR}:/data/database" \
       -v "${MEDIA_DIR}:/data/media" \
       -p "${EXTERNAL_PORT}:8000" \
       "${DOCKER_IMAGE}:${DOCKER_TAG}"
```
Where the environment variables you need are:
```
CONTAINER_NAME="hi"
HI_HOME="${HOME}/.hi"
ENV_DIR="${HI_HOME}/env"
ENV_FILE="${ENV_DIR}/local.env"
DATABASE_DIR="${HI_HOME}/database"
MEDIA_DIR="${HI_HOME}/media"
EXTERNAL_PORT="9411"
DOCKER_IMAGE="ghcr.io/cassandra/home-information"
DOCKER_TAG="${1:-latest}"
```

## Manual Installation

For users who want full control over the installation process or need to customize the setup.

### Before You Start

**Default configuration** is designed for simplicity - no user authentication, no email alerts. You can enable these later by modifying the environment file.

**Optional features to consider:**
- **Email alerts** - Get notifications when away from home (requires email provider configuration)
- **User authentication** - Require login via emailed "magic codes" (requires email configuration)

Both can be configured during manual setup or added later by editing `~/.hi/env/local.env`.

### Step-by-Step Manual Installation

#### 1. Download and Extract

Choose your project directory:
```shell
PROJ_DIR="proj"
mkdir -p $PROJ_DIR && cd $PROJ_DIR
```

Download latest release from: https://github.com/cassandra/home-information/releases/latest

Extract the code:
```shell
# Download method depends on your preference
curl -L https://github.com/cassandra/home-information/releases/latest/download/home-information.zip -o home-information.zip
unzip home-information.zip && cd home-information*

# Alternative: tarball
# tar zxvf ~/Downloads/home-information-*.tar.gz && cd home-information*
```

#### 2. Configure Environment

Generate environment configuration (includes secure admin credentials):
```shell
make env-build
```

This creates: `$HOME/.hi/env/local.env` with all necessary settings and credentials.

#### 3. Build and Run

Build the Docker image:
```shell
make docker-build
```

Start the application:
```shell
# Foreground (recommended for first run - shows errors)
make docker-run-fg

# OR background
make docker-run
```

Stop when needed:
```shell
make docker-stop
```

#### 4. Access Your Installation

**URL:** [http://localhost:9411](http://localhost:9411)

**Credentials:** Found in `$HOME/.hi/env/local.env`

**Data location:**
- Database: `$HOME/.hi/database/hi.sqlite3`
- Files: `$HOME/.hi/media`

### Manual Installation Updates

**Easiest:** Use the update script (works for any installation type):
```shell
curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/master/update.sh | bash
```

**Manual steps:**
```shell
cd $PROJ_DIR/home-information*

# Get latest code (download new release)
# Then rebuild and restart:
make docker-build
make docker-stop && make docker-run
```

## Production Deployment

Ready to deploy beyond localhost? Here's what you need to configure.

### Network Access Configuration

Edit `$HOME/.hi/env/local.env` to add your deployment URLs:
```shell
# Example: accessing via IP address and hostname
HI_EXTRA_HOST_URLS="http://192.168.1.100:9411 http://home-server:9411"
```

### Auto-Start on Reboot

The Docker container is configured to restart automatically, but Docker itself needs to start on boot:

**macOS (Docker Desktop):**
```
Docker Desktop → Settings → General → "Start Docker Desktop when you log in"
```

**Linux (Ubuntu/systemd):**
```shell
# Check if enabled
systemctl is-enabled docker

# Enable if needed
sudo systemctl enable docker
```

### User Management (Optional)

If you enabled user authentication, you'll need to create user accounts manually via the Django admin interface:

1. Sign in at [http://localhost:9411/admin/](http://localhost:9411/admin/) using:
   - Email: `DJANGO_SUPERUSER_EMAIL` (from your env file)
   - Password: `DJANGO_SUPERUSER_PASSWORD` (from your env file)

2. Add users at: [http://localhost:9411/admin/custom/customuser/add/](http://localhost:9411/admin/custom/customuser/add/)

**Requirements:** Email configuration must be working (users receive "magic code" login links)

### Integrations

Connect Home Information with your existing home automation and security systems. See the [Integrations Guide](Integrations.md) for setup instructions:
- **Home Assistant** - Device control and monitoring
- **ZoneMinder** - Security camera management

## Next Steps

### First-Time Setup
With your installation running, see the [Getting Started Guide](GettingStarted.md) for:
- Creating your first home layout
- Adding devices and information
- Setting up monitoring and alerts

## Troubleshooting

### Common Issues

**Can't access from other devices?**
- Add your network URLs to `HI_EXTRA_HOST_URLS` in `$HOME/.hi/env/local.env`
- Restart with `make docker-stop && make docker-run`

**Email alerts not working?**
Configure email settings in `$HOME/.hi/env/local.env`:
```shell
HI_EMAIL_HOST=smtp.gmail.com
HI_EMAIL_PORT=587
HI_EMAIL_HOST_USER=your-email@gmail.com
HI_EMAIL_HOST_PASSWORD=your-app-password
HI_EMAIL_USE_TLS=true
```

**User login issues?**
- Ensure email is configured (login requires "magic codes" sent via email)
- Disable authentication temporarily: `HI_SUPPRESS_AUTHENTICATION="true"`

### More Help

- **Detailed troubleshooting:** [FAQ](FAQ.md)
- **Feature questions:** [Features](Features.md)

<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Installation Guide

How to install Home Information and manage your installation day-to-day. For deployment beyond localhost (network access, custom compose stacks, production configuration), see [Deployment Options](Deployment.md).

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

## Next Steps

With your installation running, see the [Getting Started Guide](GettingStarted.md) to:
- Create your first home layout
- Add devices and information
- Set up monitoring and alerts

## Managing your installation

Manage the running app with standard Docker commands:

```shell
docker logs hi          # view logs (add -f to follow)
docker stop hi          # stop the app
docker start hi         # start it again
docker restart hi       # restart (e.g. after changing the env file)
docker ps | grep hi     # status / health
```

**Your files:**

- Configuration: `~/.hi/env/local.env`
- Database: `~/.hi/database/`
- Uploaded media: `~/.hi/media/`

## Updates

Run the update script — it pulls the latest image and recreates the container, preserving your data:

```shell
curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/master/update.sh | bash
```

## Environment Variable Changes

Edit your configuration file at `~/.hi/env/local.env`, then restart the app to pick up the changes:

```shell
docker restart hi
```

If you changed network settings such as `HI_EXTRA_HOST_URLS`, see the [Deployment Options](Deployment.md) guide for related configuration.

## Removing your installation

```shell
docker stop hi
docker rm hi
```

To also remove your data and configuration (this is permanent):

```shell
rm -rf ~/.hi/
```

## Troubleshooting

### Common Issues

**Can't access from other devices on your network?**

By default, the app only accepts requests to `localhost`. To access it from other devices (including by IP address), you need to tell the app which URLs are allowed:

- Set `HI_EXTRA_HOST_URLS` to the URL(s) you'll use to access the app, including the scheme and port
- Example: `HI_EXTRA_HOST_URLS="http://192.168.1.100:9411"` (use your server's actual IP)
- Multiple URLs can be space-separated: `HI_EXTRA_HOST_URLS="http://192.168.1.100:9411 http://myserver.local:9411"`
- For standalone Docker: edit `$HOME/.hi/env/local.env` and run `docker restart hi`
- For unRAID: set the "Extra Host URLs" field under "Show more settings"

If you see `Invalid HTTP_HOST header` errors in the logs, this is the setting you need. However, note that this setting requires the full URL location, not just a hostname.

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

- **Deployment beyond localhost** (network access, auto-start, custom compose stack, user management): [Deployment Options](Deployment.md)
- **Detailed troubleshooting:** [FAQ](FAQ.md)
- **Feature questions:** [Features](Features.md)

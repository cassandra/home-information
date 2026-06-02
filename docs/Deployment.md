<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Deployment Options

Production configuration and self-hosting options beyond a single-machine localhost install. This guide assumes you already have a working installation per the [Installation Guide](Installation.md).

## Network Access Configuration

By default, the app only accepts requests addressed to `localhost`. To access it from another device on your network (by IP address or hostname), edit `~/.hi/env/local.env` and add the URLs you'll use:

```shell
# Example: accessing via IP address and hostname
HI_EXTRA_HOST_URLS="http://192.168.1.100:9411 http://home-server:9411"
```

Multiple URLs are space-separated. After saving, restart the app: `docker restart hi`.

If you see `Invalid HTTP_HOST header` errors in the logs, this is the setting you need.

## Auto-Start on Reboot

The Docker container is configured to restart automatically (`--restart unless-stopped`), but Docker itself needs to start on boot:

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

## User Management

If you enabled user authentication, create user accounts via the Django admin interface:

1. Sign in at [http://localhost:9411/admin/](http://localhost:9411/admin/) using:
   - Email: `DJANGO_SUPERUSER_EMAIL` (from your env file)
   - Password: `DJANGO_SUPERUSER_PASSWORD` (from your env file)

2. Add users at: [http://localhost:9411/admin/custom/customuser/add/](http://localhost:9411/admin/custom/customuser/add/)

**Requirements:** Email configuration must be working (users receive "magic code" login links).

## Using docker compose directly

If you already use docker compose to manage your services, you may prefer compose verbs over the `docker logs hi` / `docker stop hi` commands documented in the Installation Guide. They are equivalent — `install.sh` generates a compose file at `~/.hi/docker-compose.yml`, so you can use either set of commands interchangeably.

```shell
cd ~/.hi
docker compose ps          # status
docker compose logs -f     # follow logs
docker compose restart     # restart
docker compose down        # stop and remove the container
docker compose up -d       # bring it back
docker compose pull && docker compose up -d   # update to latest image
```

If `docker compose` was not installed when you first ran `install.sh`, you can install it later and start using these commands immediately — the compose file is written either way.

## Integrating into your own compose stack

If you already manage your services with a single docker compose file (or directory of files), you can run Home Information from that stack instead of using `install.sh`.

Reference files in the repository root:

- [`docker-compose.example.yml`](../docker-compose.example.yml) — minimal service definition for the published image, with volumes and env file
- [`local.env.example`](../local.env.example) — the full env-var surface with placeholder values and inline documentation

Copy both files into your stack, fill in the placeholder values in `local.env`, then start the app with your usual compose commands.

**Important format note:** docker compose's `env_file` parser is **not** the same as shell-sourced env files. No `export`, no shell-style quoting (single or double quotes), no `${VAR}` interpolation. `local.env.example` is in the correct format; do not adapt a shell-sourced env file by hand without removing those features.

## Integrations

Connect Home Information with your existing home automation, security and document systems. See the [Integrations Guide](Integrations.md) for setup instructions.


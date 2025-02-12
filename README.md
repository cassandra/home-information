<img src="src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="204">

# Home Information

An application to visually organizes data about your home and the things in it. Add and place items on the screen and then attach manuals, notes, links, maintenance and repair histories or any other information for easy reference. Optionally integrate with security and home automation systems for a single view of all your house-related information.


<img src="docs/img/screenshot-kitchen.png" alt="Kitchen Example" width="250"> <img src="docs/img/screenshot-security.png" alt="Security Example" width="250"> <img src="docs/img/screenshot-cameras.png" alt="Camera Example" width="250">

## Project Status

We are looking for early adopters and contributors. The software is functional, but early in its development with many additional feature planned.

# Installation / Running

## Requirements

- Python 3 - installed
- Docker - installed and running
- Git - installed

## Installation Quick Start
``` shell
git clone git@github.com:cassandra/home-information.git
cd home-information
make env-build
make docker-build
make docker-run
```
Then visit: [http://localhost:9411](http://localhost:9411) to start.

See the [Installation Page](docs/Installation.md) for more details and troubleshooting.

To begin using the app, see the [Getting Started Page](docs/GettingStarted.md).

# Contributing / Development

## Requirements

- Python 3.11 (or higher) - installed
- Git - installed

The tech stack is:
- Django 4.2
- Javascript using jQuery 3.7
- Bootstrap 4 (CSS)
- SQLite (database)
- Redis (caching)

## Development Setup Overview

Setting up for local development looks like this:
``` shell
git clone git@github.com:cassandra/home-information.git
cd home-information
make env-build-dev
python3.11 -m venv venv
. ./init-env-dev.sh
pip install -r src/hi/requirements/development.txt
cd src
./manage.py check
./manage.py migrate
./manage.py hi_createsuperuser
./manage.py hi_creategroups
./manage.py runserver
```
See the [Development Page](docs/Development.md) for more details.

---

# Resources

- [Installation](docs/Installation.md)
- [Getting Started](docs/GettingStarted.md)
- [Development](docs/Development.md)
- [Integrations](docs/Integrations.md)
- [Contributing](docs/Contributing.md)
- [Security](docs/Security.md)
- [ChangeLog](CHANGELOG.md)
- [License](LICENSE.md)

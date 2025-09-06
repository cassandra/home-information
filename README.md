<img src="src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="204">

# Home Information

An application to visually organize data about your home and the things in it. Add and position items on the screen and then attach notes, manuals, links, maintenance and repair histories or any other information for easy visual reference. Optionally integrates with security and home automation systems for a single view of all your home-related information.

<img src="docs/img/screenshot-kitchen.png" alt="Kitchen Example" width="250"> <img src="docs/img/screenshot-security.png" alt="Security Example" width="250"> <img src="docs/img/screenshot-cameras.png" alt="Camera Example" width="250">

See the [Features Page](docs/Features.md) for more details on what this app can do.

You can also see the [Getting Started Page](docs/GettingStarted.md) to get a feel for how it looks and works.

## Project Status

We are looking for early adopters. The software is functional with all the major features now implemented.  It lacks having enough usage to work out the kinks.  We've added better styling to some parts of the app, but other visuals still need to be improved.

# Installation / Running

## Requirements

- Python 3.8+ - installed
- Docker - installed and running

## Install and Run (Quick Start)

_For those that want to run, use and/or explore the application.

Download the latest release from: https://github.com/cassandra/home-information/releases/latest and unzip or untar it.
``` shell
unzip ~/Downloads/home-information-*.zip 
cd home-information*
make env-build
make docker-build
make docker-run-fg
```
See the [Installation Page](docs/Installation.md) for more details and troubleshooting.

## Running

Run in the foreground with:
``` shell
make docker-run-fg
```
or in the background with:
``` shell
make docker-run
```

Then visit: [http://localhost:9411](http://localhost:9411) and the [Getting Started Page](docs/GettingStarted.md).

# Development

_For those that are interested in contributing or just peeking under the hood.

## Requirements

- Python 3.11 (or higher) - installed

## Tech Stack

- Django 4.2
- Javascript using jQuery 3.7
- Bootstrap 4 (CSS)
- SQLite (database)
- Redis (caching)

## Development Setup Overview

Setting up for local development, in brief, looks like this:
``` shell
# Fork the repo: https://github.com/cassandra/home-information

# Clone your fork
git clone https://github.com/${YOURUSERNAME}/home-information.git

cd home-information
./deploy/dev-setup.sh
```

See the [Contributing](CONTRIBUTING.md) and [Development](docs/Development.md) pages for more details.

---

# Resources

- [Installation](docs/Installation.md)
- [Getting Started](docs/GettingStarted.md)
- [Features](docs/Features.md)
- [Development](docs/Development.md)
- [Integrations](docs/Integrations.md)
- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security](SECURITY.md)
- [ChangeLog](CHANGELOG.md)
- [License](LICENSE.md)

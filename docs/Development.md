<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Development

## Requirements and Dependencies

- Python 3.11 (or higher) - installed
- Git - installed
- Redis - installed and running

See the [Prerequisite Installs Section](#prerequisite-installs) below if you want help installing those.

## Tech Stack

- Django 4.2 (back-end)
- Javascript using jQuery 3.7 (front-end)
- Bootstrap 4 (CSS)
- SQLite (database)
- Redis (caching)

## Development Setup

### Download

Decide where you want to download the code to and adjust the following:
``` shell
PROJ_DIR="proj"
mkdir -p $PROJ_DIR
cd $PROJ_DIR
```
Download the code:
``` shell
git clone git@github.com:cassandra/home-information.git
cd home-information
```

### Environment Setup

Generate the environment variable file and review with the command below. The file will contain sensitive secrets and are stored in a `.private` directory. Also note that administrative credentials created during this next step and save them somewhere safe.
``` shell
make env-build-dev
```
This generates an environment variable file that is sourced before running:
```
$PROJ/.private/env/development.sh
```
This directory and its files should not be checked into the code repository. There is an existing `.gitignore` entry to prevent this.


Next, create the Python virtual environment.
``` shell
cd $PROJ_DIR
python3.11 -m venv venv
```
Now source trhe environment and virtual environment with this convenience script:
``` shell
. ./init-env-dev.sh
```
In the future, just source'ing this script is all you need to set things up for development.

Next, install all the app's required Python packages.
``` shell
pip install -r src/hi/requirements/development.txt
```

### App and Database Initializations

Initialize the database and add the admin users and groups.
``` shell
cd $PROJ_DIR
cd src
./manage.py check
./manage.py migrate
./manage.py hi_createsuperuser
./manage.py hi_creategroups
```

### Running


``` shell
./manage.py runserver
```

Then, visit: [http://127.0.0.1:8411](http://127.0.0.1:8411) to access the app.

If you want to familiarize yourself with how to use the app before diving inot the code, see the [Getting Started Page](GettingStarted.md).

## Developer Documentation

The code is the best documentation for lower-level details, but there are some higher-level concepts that are useful to help orient developers. See [dev/README.md](dev/README.md) for all that high-level, developer-specific documentation.

## Contributing

See the [Contributing Page](../CONTRIBUTING.md) for guidelines and processes.

## Prerequisite Installs <a id="prerequisite-installs"></a>

_Provided for convenience. May be outdated._

### Python

#### MacOS

Get python 3.11 package and install from: [https://www.python.org/downloads/](https://www.python.org/downloads/)

#### Ubuntu (GNU/Linux)

``` shell
 sudo apt update && sudo apt upgrade
 sudo add-apt-repository ppa:deadsnakes/ppa
 sudo apt-get update
 apt list | grep python3.11
 sudo apt-get install python3.11
 sudo apt install python3.11-venv
```

### Redis

#### MacOS

Download tarball from: [https://redis.io/download](https://redis.io/download).


``` shell
brew install redis

# Yields these executables:
/usr/local/bin/redis-server 
/usr/local/bin/redis-cli 

mkdir ~/.redis
touch ~/.redis/redis.conf
```
Then run with `redis-server`.

#### Ubuntu (GNU/Linux)

``` shell
cd ~/Downloads
tar zxvf redis-6.2.1.tar.gz
cd redis-6.2.1
make test
make

sudo cp src/redis-server /usr/local/bin
sudo cp src/redis-cli /usr/local/bin

mkdir ~/.redis
touch ~/.redis/redis.conf
```
Then run with `redis-server`.

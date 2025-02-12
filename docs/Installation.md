<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Installation

## Requirements and Dependencies

- Python 3 - installed
- Docker - installed and running
- Git - installed

## Pre-install Considerations

By default, the installation does not require sign in and does not have email configure for alerts.  This is to make it as simple as possible to get started.  However, before installing, you might want to consider whether you want to enable these.  You can change these after the initial install by adjusting the environment variable file.

### Emails

The alert mechanisms have a visual and audible presentation on the screen, but to allow email alerts when away from the device, you can configure it to send emails.  This is prompted when you run the `make env-build` script (see below).

### Sign In

If you want to require sign in and authentication of users, then you will need to also configure email sending since it uses emailed "magic codes" as its authentication mechanism.  For local deployments, security might not be a major priority, so it is up to you whether you see this as a feature of annoyance.

## Installation Steps

### Running on localhost

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

#### Building

Generate the environment variable file and review with the command below. The file will contain sensitive secrets and are stored in a `.private` directory. Also note that administrative credentials created during this next step and save them somewhere safe.
``` shell
make env-build
```
This generates an environment variable file used when running:
```
$PROJ/.private/env/local.env
```
This directory and its files should not be checked into the code repository. There is an existing `.gitignore` entry to prevent this.

Build the Docker image. (This will take a while the first time.)
``` shell
make docker-build
```

#### Running

Decide if you want to run the Docker image in the foreground or background. Foreground best for first attempts as it will show the errors to the console.

The first time you run this container, it will need to do some initializations (e.g., setting up the database). It will start faster after this first time.

To run in the foreground:
``` shell
make docker-run-fg
```
Or in the background:
``` shell
make docker-run
```
When you want to stop the Docker container:
``` shell
make docker-stop
```

#### Result

The server runs on port 9411, so point your browser to: [http://localhost:9411](http://localhost:9411)

The database file and any uploaded documents live outside the Docker container in your home directory. Their default locations are: 
- Database file: `$HOME/.hi/database/hi.sqlite3`
- Uploaded files: `$HOME/.hi/media`

### Getting Started

With the server running, you are now ready to set up for your home's use.  See the [Getting Started Page](GettingStarted.md).

### Beyond localhost

When you are ready to deploy this for access to other devices, some extra steps are needed.  Web browser and Django security models enforce strict checking of hostnames, so you may need to change some of your environment configurations in the file `$PROJ/.private/env/local.env`.

#### Allowed Hosts

You will need to know what URL(s) you will be loading in the web browser and set this environment variable:
``` shell
export HI_EXTRA_HOST_URLS="${SCHEME}://${HOST}:${PORT}"
```
If you want to use more than one url, put them all in there with a space between them. e.g., Adding one for the mnemonic host name and one for accessing through its IP address.

#### User Sign In

If you have enabled requiring individual user logins, then you will need to create users manually. There is no general signup process through the app (currently), so all users need to be added using the administrator credentials using Django administrative pages.

Sign into the Django admin console using the credentials defined in the environment file as:
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

The Django admin console URL for adding users is: [http://127.0.0.1:8411/admin/custom/customuser/add/](http://127.0.0.1:8411/admin/custom/customuser/add/)

Make sure email is configured and that you use a valid email address. Login requires getting an email confirmation code.

Note: You could sign in without creating users by using the existing admin user. That is (naturally) not recommended.

#### Integrations

If you use any of the built-in integrations, so additional changes may be needed. See the 
[Integrations Page](docs/Integrations.md) for more details.

## Troubleshooting

### Emails (if enabled)

Email settings can be adjusted in env file with these settings:
``` shell
HI_EMAIL_HOST
HI_EMAIL_PORT
HI_EMAIL_HOST_USER
HI_EMAIL_HOST_PASSWORD
HI_EMAIL_USE_TLS
HI_EMAIL_USE_SSL
```
Your email provider may require configuration to allow the program to send emails.

### Sign Ins (if enabled)

Requiring sign in depends on emails. If you have problems getting email working, then disable sign in by setting the env file:
``` shell
HI_SUPPRESS_AUTHENTICATION="true"
```

## Prerequisite Installs

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

### Docker

#### MacOS

See: [https://docs.docker.com/desktop/setup/install/mac-install/](https://docs.docker.com/desktop/setup/install/mac-install/)

#### Ubuntu (GNU/Linux)

``` shell
sudo apt-get update
sudo apt-get remove docker docker-engine docker.io
sudo apt install docker.io
sudo apt install docker-compose
sudo systemctl start docker
```

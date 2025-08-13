<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Development Setup (one-time setup)

## Fork the Repository

- Sign into your GitHub account (required).
- Go to the main repository on GitHub: https://github.com/cassandra/home-information
- Click the "Fork" button in the upper-right corner. (You will be forking from the `staging` branch.)
- This creates a copy of the repository in the your GitHub account (keep same name if you can for simplicity).
- The forked repo will be located at https://github.com/${YOURUSERNAME}/home-information.git (if you kept the same repo name).

## Local Repository Setup

Decide where you want to download the code to (adjust the following):
``` shell
PROJ_DIR="${HOME}/proj"
mkdir -p $PROJ_DIR
cd $PROJ_DIR
```

Clone your fork to your local development envirnoment:
``` shell
git clone https://github.com/${YOURUSERNAME}/home-information.git

# Or use the SSH URL if you have SSH keys set up:
git clone git@github.com:${YOURUSERNAME}/home-information.git
```

Now change into that directory and configure the repo including adding the source as the "upstream" target: 
``` shell
cd home-information

git config --global user.name "${YOUR_NAME}"
git config --global user.email "${YOUR_EMAIL}"

git remote add upstream https://github.com/cassandra/home-information.git
```

Your "origin" should already be pointing to your forked repository, but check this and the "upstream" settings:
``` shell
git remote -v

# Expect
origin    https://github.com/${YOURUSERNAME}/home-information.git (fetch)
origin    https://github.com/${YOURUSERNAME}/home-information.git (push)
upstream  https://github.com/cassandra/home-information.git (fetch)
upstream  https://github.com/cassandra/home-information.git (push)
```


If your origin is not set properly, re-verify after setting with:
``` shell
git remote add origin git@github.com:${YOURUSERNAME}/home-information.git

# If no SSH keys were added to GitHub, you'll need this instead:
git remote set-url origin https://github.com/${YOURUSERNAME}/home-information.git
```

## Environment Setup

Generate the environment variable file and review with the command below. The file will contain sensitive secrets and are stored in a `.private` directory. Also note that administrative credentials created during this next step.
``` shell
make env-build-dev
```
This generates an environment variable file that we "source" before running:
```
$PROJ_DIR/.private/env/development.sh
```
This `.private` directory and its files should not be checked into the code repository. There is an existing `.gitignore` entry to prevent this.  The adminstrative credentials generated can also be seen in that file.

Next, create the Python virtual environment.
``` shell
cd $PROJ_DIR
python3.11 -m venv venv
```
Now source the environment and virtual environment with this convenience script:
``` shell
. ./init-env-dev.sh
```
In the future, just source'ing this script is all you need to set things up for development (virtual env and env vars).

Next, install all the app's required Python packages (make sure you are in the virtual env).
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

It is a good idea to run the unit tests to validate that you can and that the installation seem fine.
``` shell
./manage.py test
```

### Running

Ensure that the Redis server is running, then:

``` shell
./manage.py runserver
```

Then, visit: [http://127.0.0.1:8411](http://127.0.0.1:8411) to access the app.

If you want to familiarize yourself with how to use the app before diving inot the code, see the [Getting Started Page](../GettingStarted.md).

A look through these docs might also be a good starting point:
- [Data Model](DataModel.md)
- [Architecture](Architecture.md)


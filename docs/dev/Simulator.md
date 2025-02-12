<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Simulator

The simulator is used to simulate integrations to help test the Home Application app.

## Initialize the Simulator Database

``` shell
cd $PROJ_DIR
cd src
./simulator.py migrate
./simulator.py hi_createsuperuser
./simulator.py hi_creategroups
./simulator.py runserver
```

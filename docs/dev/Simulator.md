<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Simulator

The simulator is used to simulate integrations to help test the Home Application app.  It is a separate Django application with a separate database, though the code can be found in the `hi/simulator` directory.  There is a special `simulator.py` command along side then main Django `manage.py` script.  The `simulator.py` script acts just like the main `manage.py` script, with all the same commands (runserver, migrate, etc.), but does this to manage the simulator application.

## Initialize the Simulator Database

``` shell
cd $PROJ_DIR
cd src
./simulator.py migrate
./simulator.py hi_createsuperuser
./simulator.py hi_creategroups
./simulator.py runserver
```

Then, visit: [http://127.0.0.1:7411](http://127.0.0.1:7411) to access the simulator.

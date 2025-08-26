# Simulator Testing

There is a simulator app that lives inside the same Django code structure, but represents a completely different running application, albeit, sharing some code with the main app.  The simulator is used to simulate integrations for testing the Home Informaton app. It's a separate Django application with its own database, located in the `hi/simulator` directory. There's a special `simulator.py` command alongside the main `manage.py` script.

## Simulator Setup (Testing Integration)

### Initialize Simulator Database

```bash
cd $PROJ_DIR/src

# Simulator uses same commands as main manage.py
./simulator.py migrate
./simulator.py hi_createsuperuser
./simulator.py hi_creategroups

# Run simulator server
./simulator.py runserver
```

**Access simulator**: Visit [http://127.0.0.1:7411](http://127.0.0.1:7411)

The `simulator.py` script acts just like the main `manage.py` script with all the same commands (runserver, migrate, etc.), but manages the simulator application instead.

## Dependencies

### Python 3.11
- **macOS**: Download from python.org
- **Ubuntu**: Use deadsnakes PPA

### Redis
- **macOS**: `brew install redis`
- **Ubuntu**: Manual installation from source

### Docker (Optional)
- **macOS**: Docker Desktop
- **Ubuntu**: docker.io package

## Related Documentation
- Workflow guidelines: [Workflow Guidelines](../workflow/workflow-guidelines.md)
- Release process: [Release Process](../workflow/release-process.md)
- Dependencies: [Dependencies](../../dev/Dependencies.md)

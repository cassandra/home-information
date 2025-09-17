# Project Structure

## Directory Structure

### Top-level Directory
- `src`: application source code
- `deploy`: helper scripts and files for deploying and setting up the application
- `package`: extra items that need to be packaged up to support running the application in Docker
- `Makefile`: provides convenience wrappers around commands for building, packaging and running
- `docs`: all documentation suitable to be in markdown files

### The `src` Directory
- `hi`: entry point urls/views and some app-wide helper classes
- `hi/apps/${APPNAME}`: For normal application modules
- `hi/environment`: Environment definitions for client (Javascript) and server (Python)
- `hi/integrations`: Code for dealing with integration not related to a specific integration
- `hi/services/${SERVICENAME}`: Code for a particular integration
- `hi/simulator`: The code for the separate simulator helper app
- `hi/settings`: Django settings, including runtime population from environment variables
- `hi/static`: Static files for Javascript, CSS, IMG, etc.
- `hi/templates`: For top-level views and app-wide common base templates
- `hi/testing`: Test-specific code not used in production
- `hi/requirements`: Python package dependencies
- `custom`: Custom user model and other general customizations
- `bin`: Helper scripts needed with the code to run inside a Docker container

## Module Structure

All new files should adhere to these naming and directory organization conventions.

### Application Module Structure

**Filenames: Django Conventions**:
- `admin.py` : Django standard for Django admin models
- `apps.py` : Django standard for app metadata and initializations
- `migrations.py` : Django standard for migrations
- `models.py` : Django standard for database ORM models
- `urls.py` : Django standard for urls
- `views.py` : Django standard for views

**Filenames: App Conventions**:
- `constants.py` : For shared constants
- `context_processors.py` : For new Django context processors
- `decorators.py` : For Django decorators 
- `enums.py` : For all enums relevant to this module
- `forms.py` : For Django forms
- `middleware.py` : Django standard for middleware
- `signals.py` : For new Django signal definitions
- `transient_models.py` : For non-DB, in-memory container models with little business logic in them
- `view_mixins.py` : For view helpers that use HttpRequest/HttpResponse

**Filenames: Reserved for Auto-discovery Mechanisms**:
- `monitors.py` : For auto-discovered background monitor tasks
- `services/{app_name}/integration.py` : For auto-discovered integrations (only in `hi.services`)
- `settings.py` : For auto-discovered user-configuration options

**Filename Patterns**:
- `*_data.py` : For larger in-memory data classes needing their own module
- `*_helpers.py` : For general helpers with micellaneous responsibilities
- `*_manager.py` : For central control module, usually extending Singleton

**Directories: Django Conventions**:
- `management/commands` : Django standard for managemtn commands
- `templates` : Django standard for templates
- `templatetags` : Django standard for defining template tags

**Directories: App Conventions**:
- `assets` : For non-code files and data that business logic depends on.
- `edit` : For views and features that only apply to the apps editing mode
- `templates/tests/ui` : Templates supporting the UI testing and devtools views
- `templates/{app_name}/modals` : Templates for modal dialogs
- `templates/{app_name}/pages` : Templates representing and entire HTML page or sub-page
- `templates/{app_name}/panes` : Templates representing an HTML fragment
- `tests/data` : Non-code data supporting tests
- `tests/ui` : For develoment-only UI tests and development tools (urls.py auto-discovered)
- `tests` : All module-specifc tests go here



<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Development Guidelines

## Code Organization and Conventions

### Directories

#### Top-level Directory

- `src`: application source code (see below).
- `deploy`: helper scripts and files for deploying and setting up the application.
- `package`: extra items that need to be packaged up to support running trhe application in Docker.
- `Makefile`: provides convenience wrappers around command for building, packaging and running.
- `docs`: all documentation that suitable to be in markdown files.

#### The `src` Directory

- `hi`: entry point urls/views and some app-wide helper classes.
- `hi/templates`: For top-level views and app-wide common base templates.
- `hi/apps/${APPNAME}`: For normal application modules.
- `hi/apps/${APPNAME}/edit`: For normal application modules.
- `hi/apps/`: For normal application modules.
- `hi/integrations`: Code for dealing with integration not related to a specific integration.
- `hi/services/${SERVICENAME}`: Code for a particular integration. See the [Integrations Page](Integrations.md).
- `hi/simulator`: The code for the separate simulator helper app. See the [Simulator Page](Simulator.md).
- `hi/settings`: Django settings, including runtime population from environment variables.
- `hi/requirements`: Python package dependencies.
- `custom`: Custom user model and other general customizations.
- `bin`: Helper scripts needed with the code to run inside a Docker container.

### App Module Structure

- `enums.py`: For enums related to the module.
- `models.py`: For Django ORM models (by Django conventions).
- `transient_models.py`: For (small-ish) non-ORM models that are not persisted.
- `urls.py` - When module provides views.
- `views.py` - Main views for module.
- `views_mixin.py` - If there is common view functions needs.
- `forms.py` - If any Django forms are using in views.
- `${NAME}_manager.py` - If there is internal, persistent data the module provides, a singleton manager class is used.
- `settings.py`: If app wants to provide user-controllable settings.
- `monitors.py`: If app module needs a periodic background process.
- `templates/${APPNAME}`: The apps templates. Also see the [Templates Page](Templates.md).
- `apps.py`: Django-required module definition.
- `tests/test_${NAME}`: Unit tests for the module (by Django conventions).
- `admin.py`: For adding to Django admin console (by Django conventions).

If a module provides views or functionality that is only applicable to edit mode, then an `edit` subdirectory is used with the same structure, e.g., 

- `edit/urls.py` - UURLs if module provides edit-only views.
- `edit/views.py` - Edit-only views for module.
- etc.

## Coding Style

The project triued to adhere to PEP8 but we strongly disagree with the broadly accepted coding guidelines around spaces.  Spaces are great visual delimiters and greatly enhance readability. The whitespace deviations we make to PEP8 are shown in this Flake8 config file (`ignore`).

``` shell
[flake8]
max-line-length = 110

# Things I disable:
#
# E129 - visually indented line with same indent as next logical line
# D203 -
# E201 - whitespace after brackets
# E202 - whitespace before brackets
# E203 -
# E221 - multiple spaces before operator
# E231 - 
# E251 - unexpeced whitespace around keyword parameters
# W293 - blank line contains whitespace
# W291 - white space at end of line
# W391 - blank line at end of file
# W503 - line break before binary operator

ignore = E129,D203,E201,E202,E203,E221,E231,E251,W293,W291,W391,W503
```

## Testing Conventions

_TBD_

## Commit Messages

_TBD_

## PR Descriptions

_TBD_

## Documentation

_TBD_

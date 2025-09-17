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


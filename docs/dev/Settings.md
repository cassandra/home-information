<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Settings

## App Settings

Each internal Django app module can provide user-controllable settings that appear on the main config page.  These settings are auto-discovered by the `config` app module. The presence of a file named `settings.py` in an app module will automatically get picked up an create a new config area on the user-facing config page.

In this `settings.py` file, defined a subclass of the enum `SettingEnum` to define the label and data types.  See existing examples for details.

## Internal Settings

For help in debugging, there is a URL to inspect the Django internal `settings.py` content.
``` shell
http://localhost/config/internal
```

## Adding to an Existing setting.py

After adding a new value to and app's `SettingEnum`, you wil-l need to run `./manage.py migrate` in order to populate the database with the new setting and its default value. (New settings are written to the DB using a post-migrate signal.)

## Adding a New Tab Section to the Config UI

- Add entry to `ConfigPageType`
- Add a View - view class should extend `ConfigPageView`
- Override:
  - `config_page_type()`
  - `get_main_template_name()`
  - `get_template_context()`
- Create template (matching name)
- Should extend `config/pages/config_base.html`
- Add to `urls.py` (ensure this is included in top-level `urls.py`)

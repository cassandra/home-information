<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Settings

_TBD_

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

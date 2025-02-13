<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Django Templates

## Template naming conventions

- `pages` - For full HTML pages
- `modals` - For HTML modals
- `panes` - For all other HTML page fragments
- `email` - For email templates
- `svg` - for SVG files.

For app modules that also define some separate "edit" views, they will be in the same structure, one level down in an `edit` subdirectory.

## The "Hi Grid" Template Structure

_TBD_

### Important DIV Ids

This are gathered in `src/hi/constants.py:DIV_IDS`:

- `#hi-main-content` - This is the main display area, excluding header buttons, footer buttons and the side panel.
- `#hi-side-content`
- `#hi-top-buttons`
- `#hi-button-bottons`
- `#hi-config-integration-tab` - Integrations use this for any configuration-related views.

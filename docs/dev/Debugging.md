<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Debugging

## Custom Debug Settings

You can modify these variables in `src/hi/settings/development.py` to enable/disable some custom development features:

- `SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING` - Suppress showing the request line log message. The polling front-end will generate a long stream of these and it make it hard to see other requests.
- `SUPPRESS_MONITORS` - Turns off running any of the background monitor tasks.  Useful when working on something not related ot them to prevent unnecessary logging and resource usage.
- `BASE_URL_FOR_EMAIL_LINKS` - If needing to test the links in delivered emails. We usually need this to point back to the local development server that send the email.

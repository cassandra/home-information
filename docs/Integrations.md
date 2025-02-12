<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

ZZZ WIP


# Integrations

## ZoneMinder


### Permission Issues

zzzz
If you are going to use the zoneminder integration, then viewing the camera video streams requires requires the server to authroize the browser to allow this off-site "origin".  You will need to add the ZoneMinder URL to this envirornment variable.

export HI_EXTRA_CSP_URLS="${SCHEME}://${HOST}:${PORT}"

## Home Assistant

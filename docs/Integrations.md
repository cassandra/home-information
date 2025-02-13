<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Integrations

The current supported integrations are:
- **Home Assistant** - General home automation platform for many types of devices and protocols. Requires installation and setup.
- **ZoneMinder** - For managing security cameras with motion detection. Requires installation and setup.

To enable an integration, go to "Settings > Integrations > Add Integrations".

When you enable one of these integrations, you will need to provide the necessary connection information, usually in the way of API endpoints and credentials. 

## Home Assistant (HAss)

You will need install and set this up by following all their documentation. Start at the [Home Assistant Home Page](https://www.home-assistant.io/).

## ZoneMinder (ZM)

You will need install and set this up by following all their documentation. Start at the [ZoneMinder Home Page](https://zoneminder.com//).

### CORS Issues

If you are going to use the ZoneMinder integration, then viewing the camera video streams requires the server to authorize the browser to allow the ZoneMinder server to be an allowed off-site "origin".  You will need to add the ZoneMinder URL to an envirornment variable to have Django server up the right headers to the browser:
``` shell
export HI_EXTRA_CSP_URLS="${SCHEME}://${HOST}:${PORT}"
```

### HTTPS/SSL Issues

Another potential issue with viewing the ZoneMinder camera streams can happen if your Home Information server runs trhrough HTTP and the ZoneMinder server streams are served thruogh HTTPS/SSL.  Browsers prevent that due the security implications.  This can be made worse if the ZoneMinder server is using a self-signed SSL cert (the default?). A workaround we found was to stand up an nginx server to proxy the HTTPS/SSL urls and serve them as plain HTTP in Home Information pages by changing the ZoneMinder setting "Portal URL".


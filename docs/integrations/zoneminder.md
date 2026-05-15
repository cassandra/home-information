<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# ZoneMinder

## Overview

ZoneMinder (ZM) is an open-source video surveillance system. The ZM
integration imports each ZM monitor into Home Information (HI) as a
camera item with a motion sensor and a function controller, and
provides live video streams in the camera detail view. HI does not
run image analysis itself — motion events come from ZM's own
detection.

## Prerequisites

- A running ZoneMinder instance, network-reachable from the host
  running HI.
- An account in ZM with API access. The default `admin` account works;
  a dedicated user with API permission is recommended.
- The ZM API enabled. Recent ZM versions enable it by default; older
  installs may need it turned on in the ZM options.

## Obtaining credentials

HI authenticates against ZM with a username and password. There is no
separate API token mechanism in ZoneMinder.

1. Log in to your ZoneMinder web portal as an administrator.
2. Either use your administrator credentials, or under
   **Options → Users**, create a dedicated user for HI with API
   access enabled.
3. Note the username and password for the next section.

## Configuration values

| Field | What to enter | Notes |
|-------|---------------|-------|
| API URL | The ZM API root, e.g. `https://zm.local:8443/zm/api` | Path typically ends in `/zm/api`. Do not include a trailing slash. |
| Portal URL | The ZM web portal root, e.g. `https://zm.local:8443/zm` | Same host as API URL but without the `/api` suffix. Used for video stream URLs (`cgi-bin/nph-zms`). |
| Username | The ZM account username from the previous section. | |
| Password | The corresponding password. | Stored encrypted at rest. |
| Timezone | Your ZM server's timezone (e.g., `America/Chicago`). | ZM stores event timestamps in its server-local time; HI uses this to convert them. |
| Add Alarm Events | Whether to auto-create alarm rules for monitor motion events at import time. | Defaults to enabled. |

## Setup walkthrough

1. Open HI's integration picker (see
   [Enabling an integration](../Integrations.md#enabling-an-integration))
   and choose **ZoneMinder**.
2. Fill in the six fields above and save.
3. HI walks you through a series of modals to confirm the **Import**
   action, pull each ZM monitor as an HI camera item, and place the
   imported cameras into a location view or collection.

To pick up changes from ZoneMinder later (new monitors, renames,
removals), click **REFRESH** on the integration's manage page.

## Troubleshooting

### Camera streams will not play (CORS)

Browsers refuse to load video frames from a different origin unless
the server's Content Security Policy (CSP) explicitly allows it. If
your ZM server is on a different host or port than HI, you must add
the ZM origin to HI's allowed CSP URLs:

```shell
export HI_EXTRA_CSP_URLS="${SCHEME}://${HOST}:${PORT}"
```

Set this in the environment of the running HI process (e.g., your
service unit file or shell profile) and restart HI.

### Mixed-content errors (HTTP page, HTTPS streams)

If HI itself is served over HTTP but ZM is served over HTTPS,
browsers block the HTTPS streams from loading into the HTTP page on
security grounds. The same rejection happens — even more
aggressively — when ZM uses a self-signed certificate (the default
on many installs).

The workaround that has worked for us: stand up an nginx reverse
proxy in front of ZM that terminates SSL and serves the streams as
plain HTTP back to HI. Update ZM's **Portal URL** option to the
proxy URL so the stream paths HI generates point at the proxy
instead of the SSL endpoint.

### Connection refused / cannot reach server

The API URL or Portal URL is wrong, or the ZM server is not reachable
from the HI host. Verify by opening the Portal URL in a browser from
the HI host and confirming the ZM login page loads.

### 401 / login failures

The username or password is wrong, the user does not have API access
permission in ZM, or the ZM API is disabled. Verify by logging into
the ZM portal directly with the same credentials, then check
**Options → Users** for the user's API permission flag.

## Known limitations

- HI does not run any image analysis or motion detection — all motion
  events originate from ZM. Configure detection sensitivity and
  zones in ZM itself.
- ZM monitor renames in the upstream are propagated on Refresh; ZM
  monitor deletes remove the corresponding HI camera unless the user
  has added custom data to it (in which case it is preserved as
  detached, with a "Detached from ZoneMinder" indicator).
- Live stream playback depends on ZM's `cgi-bin/nph-zms` endpoint
  being reachable from the user's browser, not just from the HI
  server. The CORS and SSL issues above are common consequences.

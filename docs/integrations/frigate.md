<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Frigate

## Overview

[Frigate](https://frigate.video/) is an open-source NVR with built-in
object detection. The Frigate integration imports each Frigate camera
into **Home Information (HI)** as a camera item with an
object-presence sensor. **HI** consumes Frigate's HTTP API only (no
MQTT). It best serves users who want their security-camera events to
participate in HI's spatial display and rule-based alarms alongside
other integrations.

Frigate couples motion to object detection — there is no
motion-without-class signal on the events API — so each camera's
state is a single canonical object class (`person` / `car` /
`animal` / `package` / `other` / `none`) rather than a separate
motion bit and label.

## Prerequisites

- Frigate version ≥ 0.14 (tested against 0.17). Earlier versions
  may work but are not validated.
- The Frigate host must be reachable from the **HI** server and, for
  video playback, from the user's browser.
- A camera that produces a **browser-playable codec** (H.264 or
  H.265) on the stream Frigate uses for recording. Older cameras
  that only output MPEG-4 produce clips browsers cannot decode. See
  [Event clip will not play](#event-clip-will-not-play) below.

## Obtaining credentials

The integration was validated against Frigate with authentication
disabled. No credentials are required in that mode. For installs
that gate Frigate behind authentication, see
[Authentication](#authentication) at the end of this page.

## Configuration values

| Field | What to enter | Notes |
|-------|---------------|-------|
| Base URL | Frigate's API root, e.g. `http://frigate.local:5000` | No trailing slash. |
| Authorization Header | Optional verbatim `Authorization` header value. | See [Authentication](#authentication). |

## Setup walkthrough

1. Open **HI**'s integration picker (see
   [Enabling an integration](../Integrations.md#enabling-an-integration))
   and choose **Frigate**.
2. Fill in the fields above and save.
3. Click **CONNECT** to pull each Frigate camera as an **HI** camera
   item and place the imported cameras into a location view or
   collection.

To pick up upstream changes later (new cameras, renames, removals),
click **UPDATE** on the integration's manage page.

## Troubleshooting

### Camera streams or event clips will not play (CSP)

Browsers refuse to load video frames from a different origin unless
the server's Content Security Policy (CSP) explicitly allows it. If
your Frigate host is at a different origin than **HI**, add the
Frigate origin to **HI**'s allowed CSP URLs:

```shell
export HI_EXTRA_CSP_URLS="${SCHEME}://${HOST}:${PORT}"
```

Set this in the environment of the running **HI** process (e.g.,
your service unit file or shell profile) and restart **HI**.

### Event clip will not play

Symptom: the event-detail panel shows "*No video with supported
format and MIME type found*" or a similar decode error, even though
the camera and recording are working in Frigate's own UI.

Frigate records and serves event clips in whatever codec the camera
streams. If the camera outputs a codec the browser cannot decode —
most commonly MPEG-4 (the older DivX/Xvid family, not the H.264
that newer cameras default to) — the resulting clip will fail to
play.

Fixes:

- In the camera's admin UI, change the recording stream's codec to
  H.264 if it is not already.
- If the camera cannot produce H.264, configure Frigate to
  transcode the recording — see Frigate's
  [ffmpeg presets documentation](https://docs.frigate.video/configuration/ffmpeg_presets/).

### Connection refused / cannot reach Frigate

The **Base URL** is wrong, or Frigate is not reachable from the **HI**
host. Verify by opening the URL in a browser from the **HI** host
and confirming Frigate's web UI loads.

### Update finds zero cameras

Frigate's `/api/config` returned an empty `cameras` map. Confirm
your `config.yml` defines at least one camera and that Frigate is
serving that config (the web UI lists the cameras Frigate knows
about).

## Known limitations

- No MQTT support. Frigate's MQTT topics are not consumed; all
  detection events are pulled via the HTTP API.
- The per-camera state is the canonical six-value `OBJECT_PRESENCE`
  set. Raw Frigate labels (`dog`, `truck`, …) are bucketed; the
  original label is preserved on each event's detail record but is
  not directly addressable as a sensor state.
- No zone-as-state mapping. Zone names travel as event metadata but
  do not project into per-zone sensors.
- No PTZ control.
- No continuous-recording playback. Only event clips are played.
- **HI** does not run any image analysis itself — all detection
  originates from Frigate. Configure detection sensitivity, zones,
  and recording in Frigate's own config.

## Authentication

The integration was validated against Frigate with authentication
disabled — the default on a local network. For installs that gate
Frigate behind auth, the supported options are:

| Your Frigate setup | What to put in **Authorization Header** |
|---|---|
| No auth (LAN default) | Leave blank. |
| Reverse proxy with HTTP Basic auth | `Basic <base64(user:pass)>` |
| Reverse proxy with a long-lived bearer token | `Bearer <token>` |
| Reverse proxy with anonymous backend access (proxy enforces auth, but the **HI** server reaches Frigate on an internal address) | Leave blank. |
| Frigate's built-in username/password login | **Not supported in v1.** Frigate issues short-lived JWTs that require a login flow not implemented here. Workaround: front Frigate with a reverse proxy that handles auth and either expose the unauthenticated backend to **HI** on an internal network, or use one of the static schemes above. |

The value you provide is sent verbatim as the `Authorization` HTTP
header on every request to Frigate.

## References

- [Frigate documentation](https://docs.frigate.video/)
- [Frigate HTTP API reference](https://docs.frigate.video/integrations/api/frigate-http-api/)
- [Frigate ffmpeg presets](https://docs.frigate.video/configuration/ffmpeg_presets/)

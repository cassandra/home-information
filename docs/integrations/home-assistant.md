<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Home Assistant

## Overview

Home Assistant (HA) is a general-purpose home-automation platform with
broad device and protocol support. The HA integration imports HA
entities into Home Information (HI) as items and keeps their states
current via polling. For controllable items, HI dispatches control
actions back to HA.

In practice, the integration has been exercised end-to-end with
switches, outlets, open/close sensors, and motion sensors. The
default allowlist also requests other HA domains (lights, cameras,
climate, covers, locks, fans, media players) — the code attempts to
map them, but those types have not been verified against real
devices. See [Known limitations](#known-limitations).

## Prerequisites

- A running Home Assistant instance, network-reachable from the host
  running HI.
- An account in HA with permission to create a long-lived access
  token.
- HA's default REST API enabled (it is on by default in standard
  installs).

## Obtaining credentials

HI authenticates against HA using a long-lived access token.

1. In Home Assistant, click your user profile (lower-left of the
   sidebar).
2. Open the **Security** tab.
3. Scroll to **Long-lived access tokens** and click **Create
   token**.
4. Give the token a name (e.g., `home-information`) and copy the
   value. HA displays it once — store it before navigating away.

See HA's official guide for screenshots and updates if the UI changes:
[Home Assistant — Long-lived access tokens](https://www.home-assistant.io/docs/authentication/#your-account-profile).

## Configuration values

| Field | What to enter | Notes |
|-------|---------------|-------|
| Server URL | The HA root URL, e.g. `https://hass.local:8123` | No `/api` suffix — HI appends it. Trailing slash is ignored. |
| API Token | The long-lived access token from the previous section. | |
| Add Alarm Events | Whether to auto-create alarm rules for connectivity, open/close, motion, and battery sensors at import time. | Defaults to enabled. |
| Allowed Item Types | HA domains and device classes to import, one per line. Use `domain` for all classes, or `domain:class` for specific ones. | Defaults to `binary_sensor`, `camera`, `climate`, `cover`, `fan`, `light`, `lock`, `media_player`, `sensor`, `switch`. The default list reflects what the code attempts to map; only a subset (switches, outlets, open/close, motion) has been verified against real devices. Narrow the list to reduce noise from HA installs that expose many irrelevant entities. |

## Setup walkthrough

1. Open HI's integration picker (see
   [Enabling an integration](../Integrations.md#enabling-an-integration))
   and choose **Home Assistant**.
2. Fill in the four fields above and save.
3. HI walks you through a series of modals to confirm the **Import**
   action, pull HA entities that match the allowlist, and place the
   imported items into a location view or collection. Capability
   detection uses heuristics over HA's domain and device class
   metadata.

To pick up changes from HA later (new entities, renames, removals),
click **REFRESH** on the integration's manage page.

## Troubleshooting

### Connection refused / cannot reach server

The Server URL is wrong, the HA server is not reachable from the HI
host, or HA's default port is not `8123`. Verify by opening the
Server URL in a browser from the HI host and confirming the HA login
page loads.

### 401 Unauthorized

The API Token is invalid, was revoked, or was copied incompletely.
Recreate the token in HA and paste it again — HA only shows the
token value once at creation.

### Self-signed SSL certificate

If HA is served over HTTPS with a self-signed cert, browsers and
Python's TLS layer will reject it by default. Either install a
trusted certificate (e.g., via reverse proxy with Let's Encrypt) or
serve HA over plain HTTP on a trusted local network.

## Known limitations

- **Verified device coverage is narrower than the allowlist
  suggests.** Switches, outlets, open/close sensors, and motion
  sensors have been tested end-to-end. The other defaults (lights,
  cameras, climate, covers, locks, fans, media players) have code
  paths but have not been exercised against real devices — capability
  detection or control may not work as expected. If you rely on one
  of those types, expect to file issues and iterate.
- Capability detection is heuristic. HA's API does not always
  declare what an entity can do; HI infers controllability and state
  type from `domain`, `device_class`, and supported feature flags.
  Some entities may be imported as sensors when they are actually
  controllable, or vice versa.
- Multi-state HA devices (e.g., a single physical light exposed as
  both a `light.` and a `switch.` entity) are deduplicated where
  possible, but the heuristics are not perfect.
- Polling cadence is fixed; there is no push-notification path from
  HA into HI yet.

<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Frigate

> **Scaffolding placeholder.** This page is a stub created during the
> Frigate-integration scaffolding pass; the real content lands as the
> v1 feature work progresses. The shape below tracks the
> `_template.md` outline so the eventual fill is straightforward.

## Overview

The Frigate integration imports each Frigate NVR camera into
**Home Information (HI)** as a camera item with motion and
object-presence sensors. **HI** consumes Frigate's HTTP API only
(no MQTT). It best serves users who want their security-camera
events to participate in HI's spatial display and rule-based alarms
alongside other integrations.

## Prerequisites

- Frigate version: TBD (target ≥ 0.14).
- Network reachability: the Frigate web/API host must be reachable
  from the HI server.
- Authentication: v1 assumes Frigate is unauthenticated to HI (or
  fronted by an operator-managed reverse proxy). Optional
  Authorization-header value supported for installs that need it.

## Obtaining credentials

v1 typically does not require credentials — the integration only
needs Frigate's base URL. If your Frigate deployment is gated by an
auth proxy, copy the verbatim `Authorization` header value into the
optional field.

## Configuration values

- **Base URL** — e.g. `http://frigate.local:5000` (no trailing
  slash).
- **Authorization Header** — optional; verbatim header value such as
  `Bearer abc123` or `Basic <base64>`.

## Setup walkthrough

1. From the HI Settings page open the **Integrations** tab.
2. Click **Configure** on the Frigate row.
3. Enter the **Base URL**.
4. Click **Test Connection** to confirm reachability.
5. Click **Save**, then **Sync** to import the camera list.

## Troubleshooting

- *"Frigate connection probe not yet implemented"* — you're running
  pre-feature-work scaffolding; the live probe lands with the first
  feature commit.
- *"Test Connection succeeds but Sync imports zero cameras"* —
  confirm Frigate's `/api/config` returns a non-empty `cameras`
  object.

## Known limitations

- No MQTT support.
- No native object-class breakdown beyond the canonical 6-value
  `OBJECT_PRESENCE` set
  (`person` / `car` / `animal` / `package` / `other` / `none`).
- No zone-as-state mapping (zones travel as event metadata only).
- No PTZ control.
- No continuous-recording playback.
- No JWT authentication flow in v1.

## References

- [Frigate documentation](https://docs.frigate.video/)
- [Frigate HTTP API reference](https://docs.frigate.video/integrations/api/frigate-http-api/)

<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Integrations

Home Information (HI) can optionally connect to external systems to
import items from them — alongside your own items and items from any
other integrations you enable. Integrations are not required; HI
works without any of them. Each integration has its own setup steps,
credentials, and caveats — see the per-integration page for details.

You will need credentials for the upstream service before starting;
the per-integration pages below cover what to obtain and where to
enter it.

## Enabling an integration

1. In HI, click **CONFIGURE** at the bottom of the screen.
2. Select the **Integrations** tab.
3. Open the integrations picker:
   - If no integrations are configured yet, click **CONFIGURE
     INTEGRATIONS** in the main panel.
   - If at least one integration is already configured, click
     **INTEGRATIONS** at the top of the sidebar.
4. Choose the integration you want to add and follow the
   configuration steps on its per-integration page below.

## Available integrations

- **[Home Assistant](integrations/home-assistant.md)** — general-purpose
  home automation platform. Imports HA entities (lights, switches,
  sensors, cameras, climate devices, and more) and dispatches control
  actions back to HA.
- **[ZoneMinder](integrations/zoneminder.md)** — open-source video
  surveillance. Imports ZM monitors as cameras with motion sensors and
  function controllers; provides live stream playback in HI.
- **[HomeBox](integrations/homebox.md)** — home inventory tracking.
  Imports HomeBox items as read-only HI items with custom fields and
  attached files (manuals, receipts, photos).

More integrations will be added as demand arises. The per-integration
pages each carry their own troubleshooting section that accretes
real-world fixes over time — start there if something is not working.

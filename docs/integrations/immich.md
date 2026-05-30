<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Immich

## Overview

This integration lets **Home Information (HI)** search an **Immich**
self-hosted photo and video library and attach individual assets from it as
references on existing HI items and Locations. Immich does not import any
items into HI — it contributes references that get saved as links on items
you already have.  Typical use cases: link an appliance's serial-plate
photo to its HI item, attach a room photo to a Location, or save a
before/after maintenance shot to the relevant HI item or location.

## Prerequisites

- A reachable Immich server. The HI server must be able to reach
  Immich over HTTP or HTTPS at the URL you will configure;
  cross-origin browser fetches are not used, so reverse proxies are
  fine as long as the HI server can reach the address.
- An Immich user account, signed in to the Immich web UI.
- The ability to create API keys for that account.

## Obtaining credentials

1. Sign in to Immich as the user whose photo visibility you want to
   expose through HI. The API key inherits that user's visibility —
   shared and partner-shared assets are included, anything outside
   the user's view is not.
2. Click your profile picture (top-right) and choose **Account
   Settings**.
3. Open the **API Keys** section and click **New API Key**.
4. Grant at least the **`asset.read`** permission. No other scopes
   are required for this integration. Name the key something you
   will recognize later (e.g. "Home Information") and copy the
   generated key.

## Configuration values

| Field | What to enter | Notes |
|-------|---------------|-------|
| API URL | Base URL of your Immich server, e.g. `https://immich.example.com/` | Either form works (trailing slash optional). Use the same scheme + host you use in the browser. The integration appends `/api/...` paths internally. |
| API Key | The key copied from Immich's Account Settings → API Keys | Sent as the `x-api-key` header on every upstream call. Treated as a secret. |

## Setup walkthrough

Immich is configured from the **Content Sources** tab on the
Configure page (it is not on the Connectors tab — see
[Integrations](../Integrations.md) for the distinction).

1. In HI, click **CONFIGURE** at the bottom of the screen.
2. Select the **Content Sources** tab.
3. Choose **Immich** and fill in the two configuration values above.
   **Test Connection** issues a small probe against your Immich
   server and reports back; **Save** records the values.

Once Immich is configured, use it from any item or Location edit
page:

1. Click **Link Content** in the action bar to open the picker.
2. Type a query (e.g. "kitchen faucet", "serial plate", "summer
   sunset"), tick the assets you want, and click **Add Links** (the
   button shows the running count, e.g. "Add 3 Links").

Each selection becomes a new attribute on the item — the attribute's
name is the asset's filename and its value is the per-asset URL on
your Immich server. Clicking the saved link later takes you to
Immich directly (you authenticate with Immich's own session).

Search is powered by Immich's **Smart Search** (CLIP semantic
search), the same engine that drives Immich's own web UI search bar.
Natural-language queries work — you do not need to remember filenames.

## Troubleshooting

### Test Connection fails with "Immich API key not recognized"

The key was rejected (HTTP 401). Verify the key in Immich's Account
Settings → API Keys and re-paste it. Keys are sensitive to
leading/trailing whitespace. If the key was deleted in Immich, create
a new one and update the field.

### Test Connection fails with "missing the `asset.read` permission"

The key is valid but lacks the required scope (HTTP 403). Open the
key in Immich's Account Settings → API Keys and confirm `asset.read`
is granted; recreate the key if the scope cannot be added after the
fact.

### Test Connection fails with "Immich unreachable"

The HI server cannot reach the configured URL. Check the scheme
(`http` vs. `https`), hostname, and port; from a shell on the HI
server, try `curl -I <API URL>` to confirm reachability.

### Picker returns no results

Confirm the query against Immich's own web search bar as the same
user whose key you configured. If Immich's search returns nothing
for the same query, the key's user lacks visibility into the assets
you expect — try the same query while signed into Immich as that
user. Smart search is semantic, so try simpler or more concrete
terms ("blue car", "kitchen sink") rather than long descriptions.

### Picker shows a red error banner

The integration could not complete the search (auth rejected, server
unreachable, or unexpected upstream response). The banner names the
specific failure mode; use the corresponding entry above to resolve
it. The picker stays usable — you can retry after fixing the
configuration.

### Thumbnails do not load in the picker

Thumbnails are fetched through HI so the browser does not need an
Immich session. If thumbnails appear broken, check the HI logs for
`Immich thumb proxy` warnings — the upstream URL or key is likely
misconfigured. The picker still works without thumbnails; the
fallback icon is used.

### Saved links open Immich's login page

The saved link points to Immich's per-asset URL; clicking it takes
you to Immich directly, not through HI. You authenticate with
Immich's own session. If you are not signed in to Immich when you
click, Immich will prompt you.

## Known limitations

- Search uses Immich's Smart Search exclusively. Filename-only or
  strictly-structured metadata search is not exposed; Immich's own
  `/api/search/metadata` endpoint has no free-text query field, so
  there is no second mode that would meaningfully behave differently
  for typed queries.
- Videos and images both appear in results. HI only stores the
  resulting link, so the linked asset's type is Immich's concern.
- No album browsing or album-scoped search. The picker queries
  Immich's whole searchable corpus for the configured key.
- A single thumbnail size is used. The picker's responsive layout
  scales it to fit; thumbnails do not adapt per-result.
- Saved attribute links point to your Immich server's URL. If you
  later reconfigure Immich at a different host, those saved links
  will not automatically follow.
- There is no continuous sync. The integration only fetches when an
  operator opens the picker and searches. No background polling, no
  monitor health UI.
- The integration does not create HI items of its own. Assets are
  only attachable to items / Locations that already exist in HI.

<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Paperless-ngx

## Overview

This integration lets **Home Information (HI)** search a **paperless-ngx
(paperless)** server and attach documents from it as references on existing
HI items and Locations. Unlike the other integrations on the integrations
page, paperless does not import any items into HI — it contributes
references that get saved as link on items you already have. Typical use
case: link a dishwasher's warranty PDF, a thermostat's manual, or a
property's deed to the matching HI item or Location.

## Prerequisites

- A reachable paperless-ngx server (1.x or 2.x). The HI server must
  be able to reach paperless over HTTP or HTTPS at the URL you will
  configure; cross-origin browser fetches are not used, so reverse
  proxies are fine as long as the HI server can reach the address.
- A paperless user account with an API token. The token's user
  determines which documents the integration can see — give it a
  user that has the document-list permissions you want exposed
  through HI.

## Obtaining credentials

1. Sign in to paperless as the user whose document visibility you
   want to expose through HI.
2. Open the user's profile page (top-right user menu in the
   paperless web UI).
3. Click **Create token** (or **Regenerate token** if one already
   exists). Copy the generated token.
4. Keep paperless's per-user / per-group permissions in mind — the
   token sees only what its user can see.

## Configuration values

| Field | What to enter | Notes |
|-------|---------------|-------|
| API URL | Base URL of your paperless server, e.g. `https://paperless.example.com/` | Either form works (trailing slash optional). Use the same scheme + host you use in the browser. The integration appends `/api/documents/` and other paths internally. |
| API Token | The token copied from paperless's user profile | Sent as `Authorization: Token <value>` on every upstream call. Treated as a secret. |

## Setup walkthrough

Paperless is configured from the **Content Sources** tab on the
Configure page (it is not on the Connectors tab — see
[Integrations](../Integrations.md) for the distinction).

1. In HI, click **CONFIGURE** at the bottom of the screen.
2. Select the **Content Sources** tab.
3. Choose **Paperless-ngx** and fill in the two configuration values
   above. **Test Connection** issues a small probe against your
   paperless server and reports back; **Save** records the values.

Once paperless is configured, use it from any item or Location edit
page:

1. Click **Link Content** in the action bar to open the picker.
2. Type a query, tick the documents you want, and click **Add
   Links** (the button shows the running count, e.g. "Add 3 Links").

Each selection becomes a new attribute on the item — the attribute's
name is the document title and its value is the per-document URL on
your paperless server. Clicking the saved link later takes you to
paperless directly (you authenticate with paperless's own session).

## Troubleshooting

### Test Connection fails with "Paperless auth rejected"

The token was rejected (HTTP 401 or 403). Verify the token in
paperless's user profile and re-paste it. Tokens are sensitive to
leading/trailing whitespace.

### Test Connection fails with "Paperless unreachable"

The HI server cannot reach the configured URL. Check the scheme
(`http` vs. `https`), hostname, and port; from a shell on the HI
server, try `curl -I <API URL>` to confirm reachability.

### Picker returns no results

Confirm the query against paperless's own search UI as the same user
whose token you configured. If paperless's search returns nothing
for the same query, the token's user lacks visibility into the
documents you expect. If paperless's UI returns results but the
picker does not, increase the per-page count in the picker.

### Thumbnails do not load in the picker

Thumbnails are fetched through HI so the browser does not need a
paperless session. If thumbnails appear broken, check the HI logs
for `Paperless thumb proxy` warnings — the upstream URL or token
is likely misconfigured. The picker still works without thumbnails;
the fallback icon is used.

### Saved links open paperless's login page

The saved link points to paperless's per-document URL; clicking it
takes you to paperless directly, not through HI. You authenticate
with paperless's own session. If you are not signed in to paperless
when you click, paperless will prompt you.

## Known limitations

- Saved attribute links point to your paperless server's URL. If you
  later disable or reconfigure paperless (different host), those
  saved links will not automatically follow.
- There is no continuous sync. The integration only fetches when an
  operator opens the picker and searches. No background polling, no
  monitor health UI.
- The integration does not create HI items of its own. Documents are
  only attachable to items / Locations that already exist in HI.
- Search uses paperless's own full-text engine; ranking and matching
  semantics are whatever paperless provides. The picker preserves
  paperless's ordering.

<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# <img src="../../src/hi/static/img/integrations/homebox.svg" alt="HomeBox Logo" width="36"> HomeBox

## Overview

HomeBox is an open-source home inventory system for tracking
household items, warranties, and documentation. The HomeBox
integration connects or imports each HomeBox item into Home Information (HI) as
an HI item with the metadata, custom fields and attached files (manuals, receipts, photos). When used as a **Connector**, HomeBox items are shown as read-only and track to HomeBox as the source of truth. When used as a **Data Importer**, HomeBox items are copied into HI and become editable, but do not track to the original HomeBox items (HI becomes the source of truth).

## Prerequisites

- A running HomeBox instance, network-reachable from the host running
  HI.
- A HomeBox account that can sign in to the HomeBox web UI. HI uses
  the same credentials.

## Obtaining credentials

HomeBox uses the same username and password you use to log into the
HomeBox web interface — there is no separate API token to obtain.

1. Confirm your HomeBox login works in the web UI.
2. Use the same username and password in the HI configuration below.

## Configuration values

| Field | What to enter | Notes |
|-------|---------------|-------|
| API URL | The HomeBox API root, e.g. `https://homebox.local/api` | Must include the `/api` path. Do not include the version (e.g., not `/api/v1`) — HI appends the version itself. Trailing slash is ignored. |
| Username | Your HomeBox login username (or email, depending on how your HomeBox is configured). | |
| Password | Your HomeBox login password. | Stored encrypted at rest. |

## Setup walkthrough

1. Open HI's integration picker (see
   [Enabling an integration](../Integrations.md#enabling-an-integration))
   and choose **HomeBox**.
2. Fill in the three fields above and save.
3. Click **CONNECT** to pull each HomeBox item as an HI item and
   place the imported items into a location view or collection.
   Custom fields become read-only attributes; attached files are
   downloaded to HI's media storage.

To pick up changes from HomeBox later (new items, renames,
removals), click **UPDATE** on the integration's manage page.


## Troubleshooting

### Connection refused / cannot reach server

The API URL is wrong or the HomeBox server is not reachable from the
HI host. Verify by opening the API URL in a browser from the HI host
— a healthy HomeBox API root returns a JSON status response (not a
404).

### "Ensure the URL includes the API path"

The error means HI received a non-JSON response. The most common
cause is omitting the `/api` suffix from the URL — HI is hitting the
HomeBox web frontend instead of the API. Update the URL to include
`/api`.

### 401 / login failures

The username or password is wrong, or the HomeBox account is
disabled. Verify by logging into the HomeBox web UI directly with
the same credentials.

## Data Import

HomeBox also offers a one-time [Data Import](../DataImport.md)
alongside the live Integration described above. Data Import copies
your HomeBox items into HI as locally-owned entities — after import,
edits stay in HI and HomeBox is no longer consulted. Custom fields
and attached files are preserved, but maintained independently in HI
from then on.

Use Data Import when you are migrating off HomeBox, or want to
manage inventory locally without an upstream dependency. Use the
regular HomeBox Integration when you want HI to track HomeBox as the
ongoing source of truth.

See the [Data Import](../DataImport.md#importing-data) page for the
import walkthrough.

## Known limitations

- HomeBox items are imported read-only. There are no sensors,
  controllers, or alarm events for HomeBox items — they exist
  primarily for placement and reference.
- Custom attributes added in HI on a HomeBox-imported item are
  preserved across updates, but HomeBox-sourced fields cannot be
  edited from within HI; edit them in HomeBox and click **UPDATE**.
- Attached files are downloaded at Connect and on each Update.
  Replacing a file in HomeBox (a manual PDF, for instance) requires
  an Update to propagate.

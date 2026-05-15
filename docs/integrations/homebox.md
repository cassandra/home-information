<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# HomeBox

## Overview

HomeBox is an open-source home inventory system for tracking
household items, warranties, and documentation. The HomeBox
integration imports each HomeBox item into Home Information (HI) as
an HI item with the metadata and custom fields exposed as read-only
attributes; attached files (manuals, receipts, photos) are
downloaded alongside. HomeBox is an inventory source — items are
not controllable, and there are no sensors or events.

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
3. HI walks you through a series of modals to confirm the **Import**
   action, pull each HomeBox item as an HI item, and place the
   imported items into a location view or collection. Custom fields
   become read-only attributes; attached files are downloaded to
   HI's media storage.

To pick up changes from HomeBox later (new items, renames,
removals), click **REFRESH** on the integration's manage page.

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

## Known limitations

- HomeBox items are imported read-only. There are no sensors,
  controllers, or alarm events for HomeBox items — they exist
  primarily for placement and reference.
- Custom attributes added in HI on a HomeBox-imported item are
  preserved across Refresh, but HomeBox-sourced fields cannot be
  edited from within HI; edit them in HomeBox and Refresh.
- Attached files are downloaded at import / Refresh time. Updates to
  a file in HomeBox (replacing a manual PDF, for instance) require a
  Refresh to propagate.

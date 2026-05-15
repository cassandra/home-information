<!--
  TEMPLATE — copy this file to docs/integrations/<integration-name>.md
  and fill in each section.

  Goal: give a user enough to set up the integration, recognize and fix
  the most common failures, and know what this integration does and
  does not do. Short is fine — no section needs to be long. Write for
  someone who has never used HI's integrations before.
-->

<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# <Integration Name>

## Overview

One short paragraph: what this integration is for, what kinds of items
it imports into HI, and the use cases it best serves. Avoid marketing
language; describe behavior.

Introduce **Home Information (HI)** by full name on first mention,
then use the **HI** abbreviation thereafter. Same convention for
upstream services with common abbreviations (e.g., **Home Assistant
(HA)**) — full name first, abbreviation after.

Use **item** (not "entity") when referring to HI's own
representation. Reserve **entity** / **entities** for the upstream
service when that is the term that service uses (HA, for example,
calls them entities, so "HA entity" is correct in that context).

## Prerequisites

What the user must have running or installed on their side before
configuring this integration in HI. List concretely:

- Service version supported / minimum tested.
- Network reachability requirements (must be reachable from the HI
  server; same LAN; reverse proxy considerations).
- Any account, API key, or admin permission the user must already
  have.

## Obtaining credentials

Step-by-step instructions specific to this service. Use a numbered
list. Where the upstream service has its own documentation for the
step, link to it rather than restating.

Screenshots are optional but encouraged when a credential-acquisition
step is non-obvious (hidden menu, required role, etc.).

1. ...
2. ...
3. ...

## Configuration values

Map exactly what the user enters into each field of HI's Configure
form for this integration. Include URL format details that are easy to
get wrong (scheme, port, path suffix, trailing slash).

| Field | What to enter | Notes |
|-------|---------------|-------|
| ... | ... | ... |

## Setup walkthrough

What the user does in HI to enable the integration once they have
their credentials, and what to expect on the first **Import**. Keep
this brief — it is mostly continuity from the previous section into
the post-import state.

The standard first step is opening HI's integration picker — link
back to [Enabling an integration](../Integrations.md#enabling-an-integration)
for the conditional UI flow rather than restating it here, so a UI
change only needs to be reflected in one place.

Use the user-facing terms: **Import** for the first run and
**Refresh** for subsequent runs (matching the modal labels). Avoid
"sync" in user-facing copy.

## Troubleshooting

Common errors and their fixes. Treat this as an accreting list — add
entries here as real-world issues surface, rather than aiming for
completeness up front.

### <Symptom or error message>

What it usually means and how to fix it.

### <Symptom or error message>

...

## Known limitations

Things this integration does not do, or does differently from what a
new user might reasonably expect. State them plainly so users do not
spend time looking for features that are not there.

- ...
- ...

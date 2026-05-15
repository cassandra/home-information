<!--
  TEMPLATE — copy this file to docs/dev/integrations/<integration-name>.md
  and fill in each section.

  Goal: orient a developer who has never read this integration's code
  before. Keep it high-level and point at the code for details — the
  code is the authoritative source. Do not duplicate class signatures,
  method bodies, or field lists; the moment those drift, the doc
  starts misleading. Refer to file paths and class names instead.
-->

# <Integration Name>

## Overview

One paragraph on the integration's architecture: what major pieces
exist (gateway, manager, sync, monitors, client) and how they fit
together. Mention how this integration's shape differs from the
generic pattern in `integration-guidelines.md` if at all.

## Key modules

A short list of the most important files and classes a new
contributor should know about, each with a one-line description of
its role. Do not enumerate every file — pick the entry points.

- `src/hi/services/<name>/<file>.py` — `<ClassName>`. <One-line role>.
- `src/hi/services/<name>/<file>.py` — `<ClassName>`. <One-line role>.

## API patterns

Which external endpoints the integration depends on, the
authentication model, and any rate-limiting or polling cadence
considerations. State the shape; do not paste request/response bodies
(those belong in test fixtures or upstream docs).

## Implementation notes

Non-obvious decisions, workarounds, and quirks of the upstream service
that influenced the implementation. This is the section future-you
will be most grateful for. Examples of what belongs here:

- Why a specific endpoint is preferred over an obvious alternative.
- Quirks in the upstream API (inconsistent field names, eventual
  consistency windows, undocumented limits).
- Tradeoffs taken in the converter (heuristics, fallbacks).

## Testing approach

Where tests live and the mocking patterns used. If there is simulator
support for this integration, mention where (`src/hi/simulator/services/<name>/`)
and what it covers. Manual testing notes belong in
`docs/dev/testing/test-simulator.md`, not here.

## References

Links to upstream API documentation and any related internal docs.

- Upstream: <link>
- Related: <link to related internal doc, if any>

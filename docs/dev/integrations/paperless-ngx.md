# Paperless-ngx

## Overview

Paperless is the first integration to declare only the
`ATTRIBUTE_REFERENCE` capability — it has no connector, no importer,
no manager singleton, and no monitors. The gateway returns a
referencer, the referencer translates paperless's documents-search
response into `AttributeReferenceResult` rows, and a single
thumbnail-proxy view bridges the browser to the upstream API for
images embedded in the picker modal. Per-search HTTP calls happen
inline; there is no cached client.

## Key modules

- `src/hi/services/paperless/integration.py` — `PaperlessGateway`.
  Capability registration entry point; implements
  `validate_configuration` (delegates to `pl_validation`) and
  `validate_access` (single tiny upstream probe).
- `src/hi/services/paperless/pl_metadata.py` — `PaperlessMetaData`.
  Declares `integration_id = 'paperless'`, label, logo, and
  `capabilities = {ATTRIBUTE_REFERENCE}`.
- `src/hi/services/paperless/enums.py` — `PlAttributeType`. Two
  operator-configurable attributes: API URL and API token.
- `src/hi/services/paperless/pl_models.py` — `PaperlessApi`.
  Centralized wire-format strings (paths, JSON keys, auth scheme).
  Every upstream string lives here; do not inline literals
  elsewhere.
- `src/hi/services/paperless/pl_client.py` — `PaperlessClient` +
  `build_client`. Thin `requests.Session` wrapper and a factory that
  reads the configured attributes from the `Integration` row.
- `src/hi/services/paperless/pl_referencer.py` —
  `PaperlessAttributeReferencer`. Search dispatch, response
  translation, snippet extraction.
- `src/hi/services/paperless/pl_validation.py` — schema-only
  validation shared between gateway and referencer.
- `src/hi/services/paperless/views.py` + `urls.py` —
  `ThumbnailProxyView`. Mounted under
  `/integration/services/paperless/documents/<id>/thumb/`.
- `src/hi/simulator/services/paperless/` — simulator with
  parametric response shaping; see the simulator's own README-style
  comments. Used for picker / integration development without
  needing a real paperless install.

## API patterns

- **Auth**: `Authorization: Token <value>` header on every upstream
  request. Configured per-integration via `PlAttributeType.API_TOKEN`.
- **Search**: `GET <base>/api/documents/?query=<q>&page_size=<n>`.
  Returns paperless's standard DRF pagination envelope; the
  referencer reads `results` and ignores pagination cursors (the
  picker drives page size, not pagination).
- **Thumbnail**: `GET <base>/api/documents/<id>/thumb/`. Streamed
  back to the browser via the proxy view with the upstream
  `Content-Type` preserved.
- **Per-document web URL**: `<base>/documents/<id>/details/`. Used
  unchanged as the persisted `AttributeReferenceResult.source_url`;
  operators click through to paperless's own UI.
- **Probe** (validate_access): a single `page_size=1` documents-list
  request. 200 = success, 401/403 = auth failure, anything else =
  upstream failure.
- **Timeouts / rate-limiting**: client default 5 seconds; no
  back-pressure or retries beyond what `requests` does by default.
  Paperless does not rate-limit by default and picker usage is
  bounded by operator typing.

## Implementation notes

- **Thumbnail proxy, not URL passthrough**. The picker embeds
  `<img src=…>` inside HI, so the browser cannot supply the
  paperless API token. The referencer emits HI's proxy URL as
  `thumbnail_url`, and the proxy view fetches upstream with the
  configured token. Same problem HomeBox solves with
  `homebox_attachment_proxy`.
- **Source URL is NOT proxied**. The picker emits paperless's own
  per-document web URL as the persisted `source_url`. Operators
  authenticate with paperless's own session when they click the
  saved link — same UX as cut-and-paste. Proxying would couple the
  link's lifetime to HI's session.
- **No manager singleton**. ATTRIBUTE_REFERENCE has no monitors and
  no cached state, so `pl_manager.py` does not exist. `build_client`
  reads attributes from the DB on each call. If a future reason to
  cache emerges, that is the entry point to refactor through.
- **Snippet extraction client-side**. Paperless's search endpoint
  returns full document `content` per hit, not pre-built excerpts.
  The referencer extracts a ~160-char window around the matched
  query (40 chars leading) with ellipses for clipped edges.
  Falls back to a leading window when the query does not match
  verbatim (e.g., paperless matched on a stemmed form).
- **Trailing slash on API URL is forgiving**. The client normalizes
  to a trailing-slash form once at construction so operators can
  paste either form.
- **Single deployment**. The framework discovers one paperless
  integration per app directory (`integration_id = 'paperless'`).
  Multiple paperless instances are not supported; if that ever
  matters, the gateway's metadata id and the proxy URL would both
  need to become per-instance.

## Testing approach

Tests live in `src/hi/services/paperless/tests/`. Four files,
one per surface:

- `test_pl_validation.py` — schema validation (required fields,
  URL parsing, empty values).
- `test_pl_client.py` — `PaperlessClient` URL composition, auth
  header, `search_documents` / `download_thumbnail` dispatch; and
  `build_client` DB lookup including the disabled / missing /
  empty-value paths.
- `test_pl_referencer.py` — snippet-extraction edge cases and the
  end-to-end search-and-translate via a mocked `PaperlessClient`.
- `test_pl_gateway.py` — capability declaration + the
  `validate_access` probe (200 / 401 / 5xx / connection error).

All upstream HTTP is mocked via `unittest.mock`. There is no
contract test against a real paperless install; for that, run the
simulator at `src/hi/simulator/services/paperless/` (parametric
response shapes — result count, mime mix, thumbnails on/off,
snippets on/off, artificial latency) and configure the integration
against it.

## References

- Upstream API: <https://docs.paperless-ngx.com/api/>
- Capability framework: [Integration Guidelines](integration-guidelines.md)
- Picker UX: [`docs/integrations/paperless-ngx.md`](../../integrations/paperless-ngx.md)

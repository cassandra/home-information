# Immich

## Overview

Immich declares only the `EXTERNAL_REFERENCE` capability — no
connector, no importer, no manager singleton, no monitors. The
gateway returns a referencer, and the referencer translates Immich's
smart-search response into `ExternalReferenceResult` rows. Per-search
HTTP happens inline; there is no cached client. The integration
mirrors the paperless-ngx shape almost exactly — same file layout,
same lifecycle, same thumbnail-proxy pattern — with the differences
documented under [Implementation notes](#implementation-notes).

## Key modules

- `src/hi/services/immich/integration.py` — `ImmichGateway`. Gateway
  entry point; `validate_access` lives here.
- `src/hi/services/immich/im_referencer.py` —
  `ImmichExternalReferencer`. Smart-search dispatch + asset
  translation + secondary-text builder.
- `src/hi/services/immich/im_client.py` — `ImmichClient` and
  `build_client`. Thin `requests.Session` wrapper.
- `src/hi/services/immich/im_models.py` — `ImmichApi`. Wire-format
  string centralization (paths, header name, JSON keys).
- `src/hi/services/immich/views.py` — `ImmichThumbnailProxyView`.
  Server-side thumbnail fetcher.
- `src/hi/services/immich/im_validation.py` — schema-only attribute
  validation shared by gateway + referencer.
- `src/hi/simulator/services/immich/` — Immich API simulator (smart
  search, metadata-probe stub, thumbnail, photo preview).

## API patterns

Auth: `x-api-key: <value>` on every upstream call. Keys are scoped
in Immich; `asset.read` is the only scope the integration requires.

Endpoints touched at runtime:

- `POST /api/search/smart` — body `{"query": ..., "size": N}`. Used
  for every picker search.
- `GET /api/assets/<id>/thumbnail?size=thumbnail` — streamed through
  `ImmichThumbnailProxyView`.
- `<base>/photos/<id>` — Immich's per-asset web URL. Persisted
  unchanged as `source_url`; the picker links to it.

Endpoint touched at config time only:

- `POST /api/search/metadata` with body `{"size": 1}` — the
  `validate_access` probe. Cheap (no CLIP embedding) and exercises
  the same `asset.read` scope as the runtime smart endpoint.

No rate limiting or polling cadence considerations — the integration
makes one search call per picker query, no background loop.

## Implementation notes

- **Smart search only, no metadata mode.** The earlier design
  exposed `SEARCH_MODE = metadata | smart` as a config attribute.
  The `/api/search/metadata` endpoint accepts only structured filters
  (`originalFileName`, `city`, dates, camera, etc.) — there is no
  free-text `query` field, and Immich silently ignores unknown body
  keys, so an apparent "metadata text search" returned the default
  recency list regardless of input. Smart (CLIP) matches what
  Immich's own web UI search bar does, so it is the only exposed
  mode. The metadata endpoint is retained as the probe target
  because it is cheap.
- **No `_extract_snippet` analogue.** Paperless's search response
  carries full document `content`; Immich assets have nothing
  equivalent (no description field on `MetadataSearchDto`, no OCR
  text in the smart-search response). `_build_secondary_text`
  composes a short blurb from `fileCreatedAt` + `exifInfo.city` /
  `country` instead; returns `None` when neither is present so the
  picker template omits the snippet row entirely.
- **Error channel via `ExternalReferenceSearchResult.error_message`.**
  Each failure path (no config, HTTP 401, HTTP 403, generic HTTP
  failure, connectivity, unexpected) returns the dataclass with a
  named user-facing message instead of raising or returning an empty
  list. The `validate_access` probe and `search_references` use
  consistent wording for the same root causes, so operators see the
  same fix in both the configure modal and the picker banner.
- **Nested response shape.** Immich's smart-search response wraps
  results one level deeper than typical REST APIs:
  `{"assets": {"items": [...], "total": N, "count": N,
  "nextPage": null}, "albums": {...}}`. The referencer defends
  against missing `assets` and missing `items` so a shape drift
  yields an empty result list, not a crash.
- **Asset IDs are UUID strings.** The thumbnail proxy URL uses
  `<str:asset_id>`, not `<int:>` like paperless's document id.
- **Source URL is NOT proxied.** Same reasoning as paperless: the
  persisted `source_url` is Immich's own per-asset web URL.
  Operators authenticate with Immich's own session when they click.
- **No manager singleton.** Same as paperless. The client is built
  per-call from the stored attributes; `build_client` is the entry
  point to refactor through if a reason to cache emerges.
- **Single deployment.** One Immich integration per app directory.
  Multiple Immich instances are not supported.

## Testing approach

Tests live in `src/hi/services/immich/tests/` and mock all upstream
HTTP. Coverage spans client (URL/body/header shape, factory
disabled/missing/empty paths), gateway (`validate_access` 200 / 401
/ 403 / 5xx / connectivity / schema-invalid short-circuit), referencer
(search dispatch, asset translation, `_build_secondary_text` variants,
error-message paths for each failure mode), and the thumbnail proxy
view (success / upstream 404 / upstream 401 / connectivity).

For end-to-end exercise without a real Immich install, use the
simulator at `src/hi/simulator/services/immich/`. It supports
parametric response shapes (result count, EXIF on/off, artificial
latency) and a `/photos/<id>` preview page so saved source links
land somewhere instead of 404ing. Auth-failure simulation goes
through the framework-wide `ServiceFaultMode` — `AUTH_FAIL` returns
401 (key unrecognized), `FORBIDDEN` returns 403 (key lacks
`asset.read`); both exercise the corresponding distinct error
messages the integration produces.

## References

- Upstream API: <https://docs.immich.app/api/>
- Smart search semantics: <https://docs.immich.app/features/searching>
- Capability framework: [Integration Guidelines](integration-guidelines.md)
- Related: [paperless-ngx integration](paperless-ngx.md) — same
  capability shape; many design choices carry over.

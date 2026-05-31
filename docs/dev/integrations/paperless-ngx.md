# Paperless-ngx

## Capability shape

Paperless declares only the `EXTERNAL_REFERENCE` capability — no
connector, no importer, no manager singleton, no monitors. The
gateway returns a referencer, and the referencer translates
paperless's documents-search response into `ExternalReferenceResult`
rows. Per-search HTTP happens inline; there is no cached client.

## Key design decisions

- **Thumbnail proxy, not URL passthrough**. The picker embeds
  `<img src=…>` inside HI, so the browser cannot supply the
  paperless API token. The referencer emits HI's proxy URL as
  `thumbnail_url`, and the proxy view fetches upstream with the
  configured token. Same problem HomeBox solves with
  `homebox_attachment_proxy`.
- **Source URL is NOT proxied**. The persisted `source_url` is
  paperless's own per-document web URL. Operators authenticate with
  paperless's own session when they click — same UX as cut-and-paste.
  Proxying would couple the link's lifetime to HI's session.
- **No manager singleton**. EXTERNAL_REFERENCE has no monitors and
  no cached state, so there is no `pl_manager.py`. The client is
  built per-call from the stored attributes; `build_client` is the
  entry point to refactor through if a reason to cache emerges.
- **Snippet extraction client-side**. Paperless's search endpoint
  returns full document `content` per hit, not pre-built excerpts.
  The referencer extracts a short window around the matched query,
  falling back to a leading window when the query does not match
  verbatim (e.g., paperless matched on a stemmed form).
- **Single deployment**. The framework discovers one paperless
  integration per app directory. Multiple paperless instances are
  not supported; if that ever matters, the gateway's metadata id
  and the proxy URL would both need to become per-instance.

## Upstream surfaces touched

Wire-format strings live in `pl_models.py`; the integration touches
three paperless endpoints — the documents-search API, the per-document
thumbnail API (streamed through HI's proxy view), and the per-document
web URL (persisted unchanged as `source_url`). Auth is
`Authorization: Token <value>` on every upstream call.

## Testing

Tests live in `src/hi/services/paperless/tests/` and mock all upstream
HTTP. For end-to-end exercise without a real paperless install, use
the simulator at `src/hi/simulator/services/paperless/` — it supports
parametric response shapes (result count, mime mix, thumbnails on/off,
snippets on/off, artificial latency).

## References

- Upstream API: <https://docs.paperless-ngx.com/api/>
- Capability framework: [Integration Guidelines](integration-guidelines.md)

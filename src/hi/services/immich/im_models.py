class ImmichApi:
    """Wire-format strings shared by the client, referencer, gateway,
    and proxy view. Paths are appended to the configured ``API_URL``
    base; ``{id}`` is the per-asset substitution token."""

    # ---- URL paths (relative to the configured API_URL) ----

    SEARCH_SMART_PATH    = 'api/search/smart'
    # Probe-only target for ``validate_access``: structured-filter
    # endpoint that's cheap to call (no CLIP embedding) and exercises
    # the same ``asset.read`` scope as the smart endpoint used at
    # search time. We don't expose this as a search mode because it
    # has no free-text query field.
    SEARCH_METADATA_PROBE_PATH = 'api/search/metadata'
    ASSET_THUMBNAIL_PATH = 'api/assets/{id}/thumbnail'
    # Original-bytes endpoint -- used by the referencer's defensive
    # thumbnail fallback (HI-side generator from original) when the
    # upstream thumbnail endpoint is unavailable. Gated upstream on
    # image mime types so we don't pull whole videos.
    ASSET_ORIGINAL_PATH  = 'api/assets/{id}/original'
    # Per-asset web UI route. Used unchanged as the persisted attribute
    # value; operators clicking the saved link land on Immich's own
    # page (authenticated by their Immich session, not by HI).
    ASSET_WEB_PATH       = 'photos/{id}'

    # ---- Query parameters ----

    THUMBNAIL_SIZE_PARAM = 'size'
    THUMBNAIL_SIZE_VALUE = 'thumbnail'

    # ---- Search request body keys ----

    REQUEST_QUERY = 'query'
    REQUEST_SIZE  = 'size'

    # ---- Authentication ----

    AUTH_HEADER = 'x-api-key'

    # ---- Search response JSON keys ----
    # Immich nests results one level deeper than typical REST APIs:
    #   { "assets": { "items": [...], "total": N, "count": N,
    #                  "nextPage": null }, "albums": {...} }

    RESPONSE_ASSETS = 'assets'
    RESPONSE_ITEMS  = 'items'
    RESPONSE_TOTAL  = 'total'
    RESPONSE_COUNT  = 'count'

    # ---- Per-asset JSON keys ----

    ASSET_ID                 = 'id'
    ASSET_ORIGINAL_FILE_NAME = 'originalFileName'
    ASSET_ORIGINAL_MIME_TYPE = 'originalMimeType'
    ASSET_TYPE               = 'type'
    ASSET_FILE_CREATED_AT    = 'fileCreatedAt'
    ASSET_EXIF_INFO          = 'exifInfo'

    EXIF_CITY    = 'city'
    EXIF_COUNTRY = 'country'

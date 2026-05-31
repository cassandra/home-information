"""Paperless wire-format constants.

Every string that crosses the wire to a paperless-ngx server lives
here: API path templates, JSON field names in responses, and the
authorization scheme. The client and referencer pull from this
single class so a wire-side rename is a one-file edit.
"""


class PaperlessApi:
    """Wire-format strings shared between the client and the
    referencer. Paths are appended to the configured ``API_URL``
    base; ``{id}`` is the per-document substitution token."""

    # ---- URL paths (relative to the configured API_URL) ----

    DOCUMENTS_PATH       = 'api/documents/'
    DOCUMENT_THUMB_PATH  = 'api/documents/{id}/thumb/'
    # Original-bytes endpoint. Used by attach_references as the
    # fallback when the upstream thumbnail endpoint fails -- the
    # framework's thumbnail generator then makes a small PNG from
    # the original. Only fetched for mime types the generator
    # supports (image + PDF); other document types skip the fetch.
    DOCUMENT_DOWNLOAD_PATH = 'api/documents/{id}/download/'
    # Per-document web UI route. Used unchanged as the persisted
    # attribute value; operators clicking the saved link land on
    # paperless's own page (authenticated by their paperless session,
    # not by HI).
    DOCUMENT_DETAILS_PATH = 'documents/{id}/details/'

    # ---- Query parameters ----

    QUERY_PARAM     = 'query'
    PAGE_SIZE_PARAM = 'page_size'

    # ---- Authorization ----

    AUTH_HEADER = 'Authorization'
    AUTH_SCHEME = 'Token'   # ``Authorization: Token <value>``

    # ---- Documents-list response JSON keys ----

    RESPONSE_COUNT   = 'count'
    RESPONSE_RESULTS = 'results'

    # ---- Per-document JSON keys ----

    DOC_ID        = 'id'
    DOC_TITLE     = 'title'
    DOC_CONTENT   = 'content'
    DOC_MIME_TYPE = 'mime_type'

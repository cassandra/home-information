"""ATTRIBUTE_REFERENCE implementation for paperless-ngx.

Translates each paperless documents-search hit into a single
``AttributeReferenceResult``:

  - ``title``        → document title (verbatim)
  - ``source_url``   → upstream per-document URL on the configured
                       paperless server. Persisted as the saved
                       attribute's value; operators clicking the
                       saved link go directly to paperless and
                       authenticate via their own paperless session.
  - ``thumbnail_url`` → HI's thumbnail-proxy URL. The picker renders
                       this as <img src=…>; the browser's request
                       carries the HI session (not the paperless
                       API token), and HI fetches the upstream
                       thumbnail server-side.
  - ``mime_type``    → upstream document MIME (drives the picker's
                       fallback-icon path when no thumbnail).
  - ``snippet``      → ~160-char window around the query match in
                       the document's content. Paperless's search
                       endpoint returns full ``content`` per hit;
                       we extract a window client-side rather than
                       persist or display the whole document text.
"""
import logging
from typing import Optional

from django.urls import reverse
from requests import HTTPError

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.referencer.integration_referencer import (
    IntegrationAttributeReferencer,
)
from hi.integrations.referencer.transient_models import (
    AttributeReferenceResult,
    AttributeReferenceSearchResult,
)
from hi.integrations.transient_models import (
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .pl_client import PaperlessClient, build_client
from .pl_metadata import PaperlessMetaData
from .pl_models import PaperlessApi
from .pl_validation import validate_attributes


logger = logging.getLogger(__name__)


class PaperlessAttributeReferencer( IntegrationAttributeReferencer ):

    # Window cap matches the picker's snippet rendering — long
    # enough to carry useful context, short enough to keep cards
    # compact and the query visible.
    SNIPPET_WINDOW = 160
    # Characters before the matched query to include as leading
    # context. The trailing context fills the remainder up to
    # ``SNIPPET_WINDOW``.
    SNIPPET_LEAD = 40

    def get_metadata( self ) -> IntegrationMetaData:
        return PaperlessMetaData

    def validate_configuration(
            self,
            integration_attributes,
    ) -> IntegrationValidationResult:
        return validate_attributes( integration_attributes )

    def search_references(
            self,
            query : str,
            limit : int = 20,
    ) -> AttributeReferenceSearchResult:
        if not query or not query.strip():
            return AttributeReferenceSearchResult( results = [] )
        try:
            client = build_client()
        except IntegrationAttributeError as e:
            logger.warning( f'Paperless search aborted: {e}' )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = 'Paperless integration is not configured.',
            )
        except Exception as e:
            logger.exception( f'Paperless client build failed: {e}' )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = 'Paperless integration error — see server logs.',
            )

        try:
            envelope = client.search_documents(
                query = query.strip(), page_size = limit,
            )
        except HTTPError as e:
            status = getattr( e.response, 'status_code', None )
            logger.warning(
                f'Paperless search HTTP {status} for query '
                f'{query!r}: {e}'
            )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = self._http_error_message( status ),
            )
        except Exception as e:
            logger.warning(
                f'Paperless search failed for query {query!r}: {e}'
            )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = 'Paperless search failed — see server logs.',
            )

        documents = envelope.get( PaperlessApi.RESPONSE_RESULTS, [] ) or []
        return AttributeReferenceSearchResult(
            results = [
                self._translate( client = client, document = doc, query = query )
                for doc in documents
            ],
        )

    @staticmethod
    def _http_error_message( status : Optional[int] ) -> str:
        if status in (401, 403):
            return ( f'Paperless rejected the request (HTTP {status}). '
                     f'Check the API token.' )
        if status is None:
            return 'Paperless returned an unexpected response.'
        return f'Paperless returned HTTP {status}.'

    def _translate(
            self,
            client   : PaperlessClient,
            document : dict,
            query    : str,
    ) -> AttributeReferenceResult:
        document_id = document.get( PaperlessApi.DOC_ID )
        title = document.get( PaperlessApi.DOC_TITLE ) or ''
        content = document.get( PaperlessApi.DOC_CONTENT ) or ''
        mime_type = document.get( PaperlessApi.DOC_MIME_TYPE )
        return AttributeReferenceResult(
            title = title,
            source_url = client.build_document_details_url( document_id ),
            thumbnail_url = self._proxy_thumbnail_url( document_id ),
            mime_type = mime_type,
            snippet = self._extract_snippet( content = content, query = query ),
        )

    @staticmethod
    def _proxy_thumbnail_url( document_id : int ) -> str:
        # HI-internal URL that streams the upstream thumbnail through
        # the configured token. The picker renders <img src=…> so the
        # browser fetches this under HI's session.
        return reverse(
            'paperless_thumbnail',
            kwargs = { 'document_id': document_id },
        )

    @classmethod
    def _extract_snippet(
            cls, content : str, query : str,
    ) -> Optional[str]:
        """Return a short window around the query match inside the
        document content. Falls back to the document's leading
        characters when the query isn't found verbatim (e.g.,
        paperless matched on a stemmed form). Returns None when
        there is no content at all so the picker leaves the snippet
        row out entirely."""
        if not content:
            return None
        if not query:
            return cls._truncate( content, cls.SNIPPET_WINDOW )

        lowered_content = content.lower()
        lowered_query = query.strip().lower()
        idx = lowered_content.find( lowered_query )
        if idx < 0:
            return cls._truncate( content, cls.SNIPPET_WINDOW )

        start = max( 0, idx - cls.SNIPPET_LEAD )
        end = min( len(content), start + cls.SNIPPET_WINDOW )
        snippet = content[ start : end ]
        prefix = '…' if start > 0 else ''
        suffix = '…' if end < len(content) else ''
        return f'{prefix}{snippet}{suffix}'

    @staticmethod
    def _truncate( content : str, max_chars : int ) -> str:
        stripped = content.strip()
        if len(stripped) <= max_chars:
            return stripped
        return stripped[:max_chars].rstrip() + '…'

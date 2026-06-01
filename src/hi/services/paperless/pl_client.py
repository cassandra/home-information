"""HTTP client for the paperless-ngx EXTERNAL_REFERENCE integration.

The client is intentionally small: a single thin wrapper over
``requests.Session`` plus a factory that constructs one from the
stored ``Integration`` attributes. There is no manager singleton —
EXTERNAL_REFERENCE has no monitors and no cached state to own, so
each call builds a fresh client from current DB state.

The browser-facing thumbnail URL is built by the *referencer*, not
the client; the client just knows how to fetch upstream once the
caller has a document id.
"""
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration
from hi.integrations.transient_models import IntegrationKey

from .enums import PlAttributeType
from .pl_metadata import PaperlessMetaData
from .pl_models import PaperlessApi


logger = logging.getLogger(__name__)


class PaperlessClient:
    """Thin paperless-ngx HTTP client. Constructed with the
    configured base URL and API token; both are required and
    non-empty (the factory enforces this).
    """

    DEFAULT_TIMEOUT_SECS = 5.0

    def __init__(
            self,
            api_url      : str,
            token        : str,
            timeout_secs : Optional[float] = None,
    ):
        # Normalize once at construction so the API_URL is forgiving
        # whether the operator pasted with or without a trailing
        # slash. urljoin then composes paths predictably.
        self.api_url = api_url.rstrip('/') + '/'
        self.token = token
        self._timeout_secs = (
            timeout_secs if timeout_secs is not None
            else self.DEFAULT_TIMEOUT_SECS
        )
        self._session = requests.Session()
        self._session.headers.update({
            PaperlessApi.AUTH_HEADER: f'{PaperlessApi.AUTH_SCHEME} {self.token}',
        })

    def search_documents(
            self,
            query : str,
            page_size : int,
    ) -> Dict[str, Any]:
        """``GET <api_url>/api/documents/?query=<q>&page_size=<n>``;
        returns the parsed JSON envelope (count + results + …)."""
        url = urljoin( self.api_url, PaperlessApi.DOCUMENTS_PATH )
        response = self._session.get(
            url,
            params = {
                PaperlessApi.QUERY_PARAM: query,
                PaperlessApi.PAGE_SIZE_PARAM: page_size,
            },
            timeout = self._timeout_secs,
        )
        response.raise_for_status()
        return response.json()

    def download_thumbnail( self, document_id : int ) -> Dict[str, Any]:
        """Fetch the per-document thumbnail bytes from
        ``/api/documents/<id>/thumb/``. Returns
        ``{'content': bytes, 'mime_type': str}`` — the shape the
        proxy view streams back to the browser."""
        path = PaperlessApi.DOCUMENT_THUMB_PATH.format( id = document_id )
        url = urljoin( self.api_url, path )
        response = self._session.get( url, timeout = self._timeout_secs )
        response.raise_for_status()
        return {
            'content': response.content,
            'mime_type': response.headers.get(
                'Content-Type', 'application/octet-stream',
            ),
        }

    def download_original( self, document_id : int ) -> Dict[str, Any]:
        """Fetch the per-document original bytes from
        ``/api/documents/<id>/download/``. Returns
        ``{'content': bytes, 'mime_type': str}``. Callers should
        gate this on the mime type to skip formats the framework's
        thumbnail generator can't handle."""
        path = PaperlessApi.DOCUMENT_DOWNLOAD_PATH.format( id = document_id )
        url = urljoin( self.api_url, path )
        response = self._session.get( url, timeout = self._timeout_secs )
        response.raise_for_status()
        return {
            'content': response.content,
            'mime_type': response.headers.get(
                'Content-Type', 'application/octet-stream',
            ),
        }

    def build_document_details_url( self, document_id : int ) -> str:
        """Per-document web UI URL on the configured paperless server.
        Persisted as the saved attribute's value so an operator
        clicking the link later goes directly to paperless (no HI
        proxy in the path)."""
        path = PaperlessApi.DOCUMENT_DETAILS_PATH.format( id = document_id )
        return urljoin( self.api_url, path )


def build_client( timeout_secs : Optional[float] = None ) -> PaperlessClient:
    """Construct a PaperlessClient from the configured paperless
    Integration. Looks up the single (per-deployment) paperless
    integration row and reads its API_URL + API_TOKEN attributes.

    Raises:
      Integration.DoesNotExist  — paperless integration has never been
                                  configured.
      IntegrationAttributeError — required attribute is missing,
                                  empty, or the integration is
                                  disabled.
    """
    integration = Integration.objects.get(
        integration_id = PaperlessMetaData.integration_id,
    )
    if not integration.is_enabled:
        raise IntegrationAttributeError(
            'Paperless integration is disabled.'
        )

    attrs_by_key = integration.attributes_by_integration_key
    api_url = _required_attribute_value(
        attrs_by_key, PlAttributeType.API_URL,
    )
    token = _required_attribute_value(
        attrs_by_key, PlAttributeType.API_TOKEN,
    )
    return PaperlessClient(
        api_url = api_url,
        token = token,
        timeout_secs = timeout_secs,
    )


def _required_attribute_value(
        attrs_by_key : Dict[IntegrationKey, Any],
        attr_type    : PlAttributeType,
) -> str:
    key = IntegrationKey(
        integration_id = PaperlessMetaData.integration_id,
        integration_name = str( attr_type ),
    )
    attr = attrs_by_key.get( key )
    if attr is None or not (attr.value or '').strip():
        raise IntegrationAttributeError(
            f'Missing paperless attribute: {attr_type.label}'
        )
    return attr.value.strip()

import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration
from hi.integrations.transient_models import IntegrationKey

from .enums import ImAttributeType
from .im_metadata import ImmichMetaData
from .im_models import ImmichApi


logger = logging.getLogger(__name__)


class ImmichClient:

    DEFAULT_TIMEOUT_SECS = 5.0

    def __init__(
            self,
            api_url      : str,
            api_key      : str,
            timeout_secs : Optional[float] = None,
    ):
        # Normalize once at construction so the API_URL is forgiving
        # whether the operator pasted with or without a trailing
        # slash. urljoin then composes paths predictably.
        self.api_url = api_url.rstrip('/') + '/'
        self.api_key = api_key
        self._timeout_secs = (
            timeout_secs if timeout_secs is not None
            else self.DEFAULT_TIMEOUT_SECS
        )
        self._session = requests.Session()
        self._session.headers.update({
            ImmichApi.AUTH_HEADER: self.api_key,
        })

    def search_smart(
            self,
            query : str,
            size  : int,
    ) -> Dict[str, Any]:
        """``POST /api/search/smart`` -- Immich's CLIP semantic search,
        the same endpoint Immich's own web UI search bar drives. The
        sister ``/api/search/metadata`` endpoint accepts only
        structured filters (filename, EXIF, dates) and is intentionally
        not exposed here."""
        url = urljoin( self.api_url, ImmichApi.SEARCH_SMART_PATH )
        body = {
            ImmichApi.REQUEST_QUERY: query,
            ImmichApi.REQUEST_SIZE: size,
        }
        response = self._session.post(
            url, json = body, timeout = self._timeout_secs,
        )
        response.raise_for_status()
        return response.json()

    def download_thumbnail( self, asset_id : str ) -> Dict[str, Any]:
        """Fetch the per-asset thumbnail bytes. Returns
        ``{'content': bytes, 'mime_type': str}``."""
        path = ImmichApi.ASSET_THUMBNAIL_PATH.format( id = asset_id )
        url = urljoin( self.api_url, path )
        response = self._session.get(
            url,
            params = { ImmichApi.THUMBNAIL_SIZE_PARAM: ImmichApi.THUMBNAIL_SIZE_VALUE },
            timeout = self._timeout_secs,
        )
        response.raise_for_status()
        return {
            'content': response.content,
            'mime_type': response.headers.get(
                'Content-Type', 'application/octet-stream',
            ),
        }

    def download_original( self, asset_id : str ) -> Dict[str, Any]:
        """Fetch the per-asset original bytes. Returns
        ``{'content': bytes, 'mime_type': str}``. Callers should
        gate this on the mime type (image only) to avoid pulling
        whole videos."""
        path = ImmichApi.ASSET_ORIGINAL_PATH.format( id = asset_id )
        url = urljoin( self.api_url, path )
        response = self._session.get( url, timeout = self._timeout_secs )
        response.raise_for_status()
        return {
            'content': response.content,
            'mime_type': response.headers.get(
                'Content-Type', 'application/octet-stream',
            ),
        }

    def build_asset_web_url( self, asset_id : str ) -> str:
        """Per-asset web UI URL on the configured Immich server.
        Persisted as the saved attribute's value so an operator
        clicking the link later goes directly to Immich (no HI proxy
        in the path)."""
        path = ImmichApi.ASSET_WEB_PATH.format( id = asset_id )
        return urljoin( self.api_url, path )


def build_client( timeout_secs : Optional[float] = None ) -> ImmichClient:
    """Construct an ImmichClient from the configured Immich
    Integration row.

    Raises:
      Integration.DoesNotExist  -- Immich integration never configured.
      IntegrationAttributeError -- required attribute missing or empty,
                                  or integration disabled.
    """
    integration = Integration.objects.get(
        integration_id = ImmichMetaData.integration_id,
    )
    if not integration.is_enabled:
        raise IntegrationAttributeError(
            'Immich integration is disabled.'
        )

    attrs_by_key = integration.attributes_by_integration_key
    api_url = _required_attribute_value(
        attrs_by_key, ImAttributeType.API_URL,
    )
    api_key = _required_attribute_value(
        attrs_by_key, ImAttributeType.API_KEY,
    )
    return ImmichClient(
        api_url = api_url,
        api_key = api_key,
        timeout_secs = timeout_secs,
    )


def _required_attribute_value(
        attrs_by_key : Dict[IntegrationKey, Any],
        attr_type    : ImAttributeType,
) -> str:
    key = IntegrationKey(
        integration_id = ImmichMetaData.integration_id,
        integration_name = str( attr_type ),
    )
    attr = attrs_by_key.get( key )
    if attr is None or not (attr.value or '').strip():
        raise IntegrationAttributeError(
            f'Missing Immich attribute: {attr_type.label}'
        )
    return attr.value.strip()

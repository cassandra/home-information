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

from .im_client import ImmichClient, build_client
from .im_metadata import ImmichMetaData
from .im_models import ImmichApi
from .im_validation import validate_attributes


logger = logging.getLogger(__name__)


class ImmichAttributeReferencer( IntegrationAttributeReferencer ):

    def get_metadata( self ) -> IntegrationMetaData:
        return ImmichMetaData

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
            logger.warning( f'Immich search aborted: {e}' )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = 'Immich integration is not configured.',
            )
        except Exception as e:
            logger.exception( f'Immich client build failed: {e}' )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = 'Immich integration error — see server logs.',
            )

        try:
            envelope = client.search_smart(
                query = query.strip(), size = limit,
            )
        except HTTPError as e:
            status = getattr( e.response, 'status_code', None )
            logger.warning(
                f'Immich search HTTP {status} for query '
                f'{query!r}: {e}'
            )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = self._http_error_message( status ),
            )
        except Exception as e:
            logger.warning(
                f'Immich search failed for query {query!r}: {e}'
            )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = 'Immich search failed — see server logs.',
            )

        items = (
            envelope.get( ImmichApi.RESPONSE_ASSETS, {} )
            or {}
        ).get( ImmichApi.RESPONSE_ITEMS, []) or []
        try:
            results = [
                self._translate( client = client, asset = asset )
                for asset in items
            ]
        except Exception as e:
            # Per-asset translation can fail on shape drift (missing
            # id, etc.). Surface as the same unexpected-response
            # signal the HTTP layer uses so the picker banner names
            # the integration instead of falling to the framework's
            # generic fallback message.
            logger.warning(
                f'Immich asset translation failed for query '
                f'{query!r}: {e}'
            )
            return AttributeReferenceSearchResult(
                results = [],
                error_message = self._http_error_message( None ),
            )
        return AttributeReferenceSearchResult( results = results )

    @staticmethod
    def _http_error_message( status : Optional[int] ) -> str:
        if status == 401:
            return 'Immich API key not recognized (HTTP 401).'
        if status == 403:
            return ( 'Immich API key is missing the asset.read '
                     'permission (HTTP 403).' )
        if status is None:
            return 'Immich returned an unexpected response.'
        return f'Immich returned HTTP {status}.'

    def _translate(
            self,
            client : ImmichClient,
            asset  : dict,
    ) -> AttributeReferenceResult:
        asset_id = asset.get( ImmichApi.ASSET_ID )
        title = (
            asset.get( ImmichApi.ASSET_ORIGINAL_FILE_NAME )
            or asset_id
            or ''
        )
        return AttributeReferenceResult(
            title = title,
            source_url = client.build_asset_web_url( asset_id ),
            thumbnail_url = self._proxy_thumbnail_url( asset_id ),
            mime_type = asset.get( ImmichApi.ASSET_ORIGINAL_MIME_TYPE ),
            snippet = self._build_secondary_text( asset ),
        )

    @staticmethod
    def _proxy_thumbnail_url( asset_id : str ) -> str:
        return reverse(
            'immich_thumbnail',
            kwargs = { 'asset_id': asset_id },
        )

    @staticmethod
    def _build_secondary_text( asset : dict ) -> Optional[str]:
        """Compose a short secondary-text line from the asset's
        created-date and EXIF city/country. Returns None when neither
        signal is present -- the picker template omits the snippet row
        entirely on None. Photos have no full-text content, so the
        snippet exists to give the operator something to disambiguate
        otherwise-identical filenames."""
        parts = []
        created_at = asset.get( ImmichApi.ASSET_FILE_CREATED_AT )
        if created_at:
            # Immich emits ISO 8601; keep just the date portion. We
            # avoid datetime parsing -- defensiveness against shape
            # drift matters more than perfect formatting here.
            parts.append( str(created_at)[:10] )

        exif = asset.get( ImmichApi.ASSET_EXIF_INFO ) or {}
        place = [
            exif.get( ImmichApi.EXIF_CITY ),
            exif.get( ImmichApi.EXIF_COUNTRY ),
        ]
        place_str = ', '.join( p for p in place if p )
        if place_str:
            parts.append( place_str )

        if not parts:
            return None
        return ' · '.join( parts )

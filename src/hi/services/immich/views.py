import logging

from django.http import Http404, HttpResponse
from django.views import View
from requests import HTTPError

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration

from .im_client import build_client


logger = logging.getLogger(__name__)


class ImmichThumbnailProxyView( View ):

    def get( self, request, asset_id : str ):
        try:
            client = build_client()
        except (Integration.DoesNotExist, IntegrationAttributeError):
            raise Http404('Immich integration not configured.')

        try:
            downloaded = client.download_thumbnail( asset_id = asset_id )
        except HTTPError as e:
            status = getattr( e.response, 'status_code', None )
            if status == 404:
                raise Http404('Thumbnail not found.')
            logger.warning(
                f'Immich thumb proxy HTTP {status} '
                f'for asset {asset_id}: {e}'
            )
            return HttpResponse(
                status = 502, content = 'Immich upstream error.',
            )
        except Exception as e:
            logger.warning(
                f'Immich thumb proxy failed '
                f'for asset {asset_id}: {e}'
            )
            return HttpResponse(
                status = 502, content = 'Immich upstream error.',
            )

        return HttpResponse(
            content = downloaded['content'],
            content_type = downloaded['mime_type'],
        )

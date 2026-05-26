"""Browser-facing paperless views.

Only a thumbnail proxy lives here. Document source links go directly
to paperless's web UI (the operator authenticates with paperless via
their own session), but thumbnails are embedded inside the HI picker
modal so the browser cannot supply the upstream API token. The proxy
fetches server-side with the configured token and streams bytes back
under HI's session — same approach HomeBox uses for its attachments.
"""
import logging

from django.http import Http404, HttpResponse
from django.views import View
from requests import HTTPError

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration

from .pl_client import build_client

logger = logging.getLogger(__name__)


class ThumbnailProxyView( View ):

    def get( self, request, document_id : int ):
        try:
            client = build_client()
        except (Integration.DoesNotExist, IntegrationAttributeError):
            raise Http404('Paperless integration not configured.')

        try:
            downloaded = client.download_thumbnail(
                document_id = document_id,
            )
        except HTTPError as e:
            status = getattr( e.response, 'status_code', None )
            if status == 404:
                raise Http404('Thumbnail not found.')
            logger.warning(
                f'Paperless thumb proxy HTTP {status} '
                f'for document {document_id}: {e}'
            )
            return HttpResponse(
                status = 502, content = 'Paperless upstream error.',
            )
        except Exception as e:
            # Upstream connectivity / auth / parse failure. Surface
            # as 502 so the browser distinguishes upstream trouble
            # from a missing document.
            logger.warning(
                f'Paperless thumb proxy failed '
                f'for document {document_id}: {e}'
            )
            return HttpResponse(
                status = 502, content = 'Paperless upstream error.',
            )

        return HttpResponse(
            content = downloaded['content'],
            content_type = downloaded['mime_type'],
        )

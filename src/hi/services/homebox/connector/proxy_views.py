"""
HomeBox attachment proxy. HomeBox requires bearer-token auth so the
browser cannot fetch attachments directly; the proxy fetches
server-side and streams bytes back with the upstream content-type.
"""
import logging

from django.http import Http404, HttpResponse
from django.views import View

from hi.apps.entity.models import Entity
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_manager import HomeBoxManager

logger = logging.getLogger(__name__)


class HomeBoxAttachmentProxyView(View):

    def get(self, request, entity_id: int, attachment_id: str):
        try:
            entity = Entity.objects.get(
                pk=entity_id,
                integration_id=HbMetaData.integration_id,
            )
        except Entity.DoesNotExist:
            raise Http404('Entity not found or not a HomeBox entity.')

        item_id = entity.integration_name
        if not item_id:
            raise Http404('Entity has no HomeBox item id.')

        hb_manager = HomeBoxManager()
        hb_manager.ensure_initialized()
        if not hb_manager.hb_client:
            return HttpResponse(status=503, content='HomeBox integration unavailable.')

        try:
            downloaded = hb_manager.hb_client.download_attachment(
                item_id=item_id,
                attachment_id=attachment_id,
            )
        except Exception as e:
            # Upstream connectivity / auth / HTTP failure during the
            # download itself. Surface as a 502 (bad gateway) rather
            # than 404 so the browser and ops can tell upstream
            # trouble apart from a genuinely-missing attachment.
            logger.warning(
                f'HomeBox attachment proxy: download failed for entity '
                f'{entity_id} attachment {attachment_id}: {e}'
            )
            return HttpResponse(status=502, content='HomeBox upstream error.')

        if not downloaded:
            raise Http404('Attachment not returned by HomeBox.')

        content = downloaded.get('content')
        mime_type = downloaded.get('mime_type') or 'application/octet-stream'
        if content is None:
            raise Http404('Attachment empty.')

        return HttpResponse(content=content, content_type=mime_type)

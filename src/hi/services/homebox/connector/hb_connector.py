"""
HomeBox Connect-mode resolver. Fetches the live HomeBox item state
on each modal open; returns ``StructuredViewData`` on success or
``MinimalViewData`` on failure.
"""
import logging
from typing import List, Optional
from urllib.parse import urljoin

from django.urls import reverse

from hi.apps.entity.models import Entity
from hi.integrations.external_view_data import (
    AttachmentRef,
    ExternalViewData,
    MinimalViewData,
    NameValuePair,
    StructuredViewData,
)

from hi.services.homebox.shared.hb_converter import HB_ITEM_FIELD_PAIRS
from hi.services.homebox.shared.hb_manager import HomeBoxManager
from hi.services.homebox.shared.hb_models import HbItem

logger = logging.getLogger(__name__)


class HomeBoxConnector:
    """Stateless resolver for the entity-detail external-data view hook."""

    def get_external_view_data(self, entity: Entity) -> Optional[ExternalViewData]:
        item_id = entity.integration_name
        if not item_id:
            return None

        deep_link_url = self._build_deep_link_url(item_id)

        try:
            hb_manager = HomeBoxManager()
            hb_manager.ensure_initialized()
            hb_item = hb_manager.fetch_hb_item_from_api(item_id=item_id, verbose=False)
        except Exception as e:
            logger.warning(
                f'HomeBox Connect resolver: failed to fetch item {item_id} '
                f'for entity {entity.id}: {e}'
            )
            return MinimalViewData(
                deep_link_url=deep_link_url,
                error_message=f'HomeBox upstream unavailable: {e}',
            )

        return StructuredViewData(
            deep_link_url=deep_link_url,
            attributes=self._build_attributes(hb_item),
            attachments=self._build_attachments(entity, hb_item),
        )

    def _build_attributes(self, hb_item: HbItem) -> List[NameValuePair]:
        rows: List[NameValuePair] = []

        for prop_name, label in HB_ITEM_FIELD_PAIRS:
            value = getattr(hb_item, prop_name, None)
            if value is None:
                continue
            value_str = str(value).strip()
            if not value_str:
                continue
            rows.append(NameValuePair(name=label, value=value_str))

        for hb_field in (hb_item.fields or []):
            if not isinstance(hb_field, dict):
                continue
            name = str(hb_field.get('name', '')).strip()
            value = str(hb_field.get('textValue', '')).strip()
            if not name or not value:
                continue
            rows.append(NameValuePair(name=name, value=value))

        tags = hb_item.tags or []
        tag_names = [
            str(tag.get('name', '')).strip()
            for tag in tags
            if isinstance(tag, dict) and str(tag.get('name', '')).strip()
        ]
        if tag_names:
            rows.append(NameValuePair(name='Tags', value=', '.join(tag_names)))

        return rows

    def _build_attachments(self, entity: Entity, hb_item: HbItem) -> List[AttachmentRef]:
        refs: List[AttachmentRef] = []
        for attachment in (hb_item.attachments or []):
            if not isinstance(attachment, dict):
                continue
            attachment_id = str(attachment.get('id', '') or '').strip()
            if not attachment_id:
                continue
            title = str(attachment.get('title', '') or '').strip() or f'Attachment {attachment_id}'
            mime_type = str(attachment.get('mimeType', '') or '').strip()

            attachment_url = self._build_proxy_url(entity.id, attachment_id)

            thumbnail_id = ''
            thumbnail_info = attachment.get('thumbnail')
            if isinstance(thumbnail_info, dict):
                thumbnail_id = str(thumbnail_info.get('id', '') or '').strip()
            thumbnail_url = (
                self._build_proxy_url(entity.id, thumbnail_id)
                if thumbnail_id else None
            )

            refs.append(AttachmentRef(
                id=attachment_id,
                title=title,
                mime_type=mime_type,
                thumbnail_url=thumbnail_url,
                open_url=attachment_url,
            ))
        return refs

    def _build_proxy_url(self, entity_id: int, attachment_id: str) -> str:
        return reverse(
            'homebox_attachment_proxy',
            kwargs={'entity_id': entity_id, 'attachment_id': attachment_id},
        )

    def _build_deep_link_url(self, item_id: str) -> Optional[str]:
        """Best-effort: strip a trailing ``/api`` from the configured
        URL and append ``/item/<id>``. Returns None if no API URL is
        configured."""
        hb_manager = HomeBoxManager()
        if not hb_manager.hb_client:
            return None
        api_url = hb_manager.hb_client.api_url
        if not api_url:
            return None
        if api_url.endswith('/api'):
            web_base = api_url[:-len('/api')]
        else:
            web_base = api_url
        return urljoin(web_base + '/', f'item/{item_id}')

"""
Tests for the HomeBox attachment proxy view.

Covers the bearer-token proxy that streams HomeBox attachments and
thumbnails back to the browser: 404s for unknown / non-HomeBox
entities, 503 when the integration's client is unavailable, 502 on
upstream download failure, and a clean 200 with passthrough bytes
and content-type on success.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse

from hi.apps.entity.models import Entity
from hi.services.homebox.hb_metadata import HbMetaData


logging.disable(logging.CRITICAL)


class HomeBoxAttachmentProxyViewTests(TestCase):

    def _make_hb_entity(self, item_id: str = '42') -> Entity:
        return Entity.objects.create(
            name=f'HomeBox Item {item_id}',
            entity_type_str='LIGHT',
            integration_id=HbMetaData.integration_id,
            integration_name=item_id,
        )

    def _url(self, entity_id: int, attachment_id: str = 'att-1') -> str:
        return reverse(
            'homebox_attachment_proxy',
            kwargs={'entity_id': entity_id, 'attachment_id': attachment_id},
        )

    def test_unknown_entity_returns_404(self):
        url = self._url(entity_id=99999, attachment_id='att-1')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_non_homebox_entity_returns_404(self):
        entity = Entity.objects.create(
            name='Native Entity',
            entity_type_str='LIGHT',
        )
        response = self.client.get(self._url(entity.id))
        self.assertEqual(response.status_code, 404)

    def test_returns_503_when_client_unavailable(self):
        entity = self._make_hb_entity('1')

        manager = Mock()
        manager.hb_client = None
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.proxy_views.HomeBoxManager',
            return_value=manager,
        ):
            response = self.client.get(self._url(entity.id))

        self.assertEqual(response.status_code, 503)

    def test_successful_download_returns_bytes_and_mime(self):
        entity = self._make_hb_entity('1')

        manager = Mock()
        client = Mock()
        client.download_attachment.return_value = {
            'content': b'PNG-BYTES',
            'mime_type': 'image/png',
        }
        manager.hb_client = client
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.proxy_views.HomeBoxManager',
            return_value=manager,
        ):
            response = self.client.get(self._url(entity.id, attachment_id='att-1'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'PNG-BYTES')
        self.assertEqual(response['Content-Type'], 'image/png')
        client.download_attachment.assert_called_once_with(
            item_id='1', attachment_id='att-1',
        )

    def test_download_returns_none_results_in_404(self):
        entity = self._make_hb_entity('1')

        manager = Mock()
        client = Mock()
        client.download_attachment.return_value = None
        manager.hb_client = client
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.proxy_views.HomeBoxManager',
            return_value=manager,
        ):
            response = self.client.get(self._url(entity.id))

        self.assertEqual(response.status_code, 404)

    def test_download_raises_results_in_502(self):
        """Upstream connectivity / auth failure surfaces as 502 (bad
        gateway) so the browser and ops can distinguish upstream
        trouble from a genuinely-missing attachment."""
        entity = self._make_hb_entity('1')

        manager = Mock()
        client = Mock()
        client.download_attachment.side_effect = RuntimeError('boom')
        manager.hb_client = client
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.proxy_views.HomeBoxManager',
            return_value=manager,
        ):
            response = self.client.get(self._url(entity.id))

        self.assertEqual(response.status_code, 502)

    def test_missing_content_returns_404(self):
        entity = self._make_hb_entity('1')

        manager = Mock()
        client = Mock()
        client.download_attachment.return_value = {
            'content': None,
            'mime_type': 'image/png',
        }
        manager.hb_client = client
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.proxy_views.HomeBoxManager',
            return_value=manager,
        ):
            response = self.client.get(self._url(entity.id))

        self.assertEqual(response.status_code, 404)

    def test_default_mime_when_upstream_omits(self):
        entity = self._make_hb_entity('1')

        manager = Mock()
        client = Mock()
        client.download_attachment.return_value = {
            'content': b'raw',
            'mime_type': None,
        }
        manager.hb_client = client
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.proxy_views.HomeBoxManager',
            return_value=manager,
        ):
            response = self.client.get(self._url(entity.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')

    def test_entity_with_no_integration_name_returns_404(self):
        # HomeBox-integrated entity but somehow missing item id.
        entity = Entity.objects.create(
            name='Broken HomeBox Entity',
            entity_type_str='LIGHT',
            integration_id=HbMetaData.integration_id,
            integration_name='',
        )
        response = self.client.get(self._url(entity.id))
        self.assertEqual(response.status_code, 404)

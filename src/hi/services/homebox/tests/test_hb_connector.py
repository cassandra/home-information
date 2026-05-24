"""
Tests for the HomeBox Connect-mode resolver.

Covers the entity-detail external-data view hook: native entities
(no integration_name) return None; upstream-unavailable returns a
MinimalViewData; successful fetch returns a StructuredViewData with
documented fields, custom fields, tags, and attachments (with proxy
URLs for thumbnails/downloads).
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.entity.models import Entity
from hi.integrations.connect.external_view_data import (
    MinimalViewData,
    NameValuePair,
    StructuredViewData,
)
from hi.services.homebox.connector.hb_connector import HomeBoxConnector
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.shared.hb_models import HbItem


logging.disable(logging.CRITICAL)


class HomeBoxConnectorTests(TestCase):

    def _make_hb_entity(self, item_id: str = '42') -> Entity:
        return Entity.objects.create(
            name=f'HomeBox Item {item_id}',
            entity_type_str='LIGHT',
            integration_id=HbMetaData.integration_id,
            integration_name=item_id,
        )

    def _make_native_entity(self) -> Entity:
        return Entity.objects.create(
            name='Native Entity',
            entity_type_str='LIGHT',
        )

    def test_returns_none_for_native_entity(self):
        entity = self._make_native_entity()
        connector = HomeBoxConnector()
        result = connector.get_external_view_data(entity)
        self.assertIsNone(result)

    def test_returns_minimal_when_upstream_fetch_raises(self):
        entity = self._make_hb_entity('42')

        manager = Mock()
        manager.hb_client = Mock()
        manager.hb_client.api_url = 'http://homebox.example.com/api'
        manager.fetch_hb_item_from_api.side_effect = RuntimeError('unreachable')
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxManager',
            return_value=manager,
        ):
            result = HomeBoxConnector().get_external_view_data(entity)

        self.assertIsInstance(result, MinimalViewData)
        self.assertEqual(result.deep_link_url, 'http://homebox.example.com/item/42')
        self.assertIsNotNone(result.error_message)
        self.assertIn('unreachable', result.error_message)

    def test_returns_minimal_when_client_unavailable(self):
        # Manager initialized but client is None (e.g., disabled
        # integration). The resolver still attempts a fetch, which
        # raises IntegrationError from the manager; the resolver
        # catches it and returns MinimalViewData. Since client is
        # None, the deep link URL cannot be derived and stays None.
        entity = self._make_hb_entity('99')

        manager = Mock()
        manager.hb_client = None
        manager.fetch_hb_item_from_api.side_effect = RuntimeError('no client')
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxManager',
            return_value=manager,
        ):
            result = HomeBoxConnector().get_external_view_data(entity)

        self.assertIsInstance(result, MinimalViewData)
        self.assertIsNone(result.deep_link_url)
        self.assertIsNotNone(result.error_message)
        self.assertIn('no client', result.error_message)

    def test_successful_fetch_returns_structured_data_with_field_ordering(self):
        entity = self._make_hb_entity('123')

        hb_item = HbItem(api_dict={
            'id': '123',
            'name': 'Drill',
            'description': 'Cordless drill',
            'manufacturer': 'Acme',
            'modelNumber': 'X-99',
            'serialNumber': '',  # blank, must be skipped
            'assetId': 'A-1',
            'purchaseFrom': '',  # blank, must be skipped
            'purchaseTime': '2024-01-15',
            'warrantyDetails': '',
            'warrantyExpires': '2026-01-15',
            'notes': 'Garage shelf',
            'fields': [
                {'name': 'Bit Set', 'textValue': 'Phillips'},
                {'name': '', 'textValue': 'no-name-skip'},
                {'name': 'Empty', 'textValue': ''},
                'not-a-dict',
            ],
            'tags': [
                {'name': 'tools'},
                {'name': 'garage'},
                {'name': ''},
                'not-a-dict',
            ],
        })

        manager = Mock()
        manager.hb_client = Mock()
        manager.hb_client.api_url = 'http://homebox.example.com/api'
        manager.fetch_hb_item_from_api.return_value = hb_item
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxManager',
            return_value=manager,
        ):
            result = HomeBoxConnector().get_external_view_data(entity)

        self.assertIsInstance(result, StructuredViewData)
        self.assertEqual(result.deep_link_url, 'http://homebox.example.com/item/123')

        # Documented fields, in ITEM_FIELD_PAIRS order, blanks skipped.
        # Custom fields appended next. Tags last.
        expected_pairs = [
            ('Description', 'Cordless drill'),
            ('Manufacturer', 'Acme'),
            ('Model Number', 'X-99'),
            ('Asset ID', 'A-1'),
            ('Purchase Date', '2024-01-15'),
            ('Warranty Expires', '2026-01-15'),
            ('Notes', 'Garage shelf'),
            ('Bit Set', 'Phillips'),
            ('Tags', 'tools, garage'),
        ]
        actual_pairs = [(row.name, row.value) for row in result.attributes]
        self.assertEqual(actual_pairs, expected_pairs)
        for row in result.attributes:
            self.assertIsInstance(row, NameValuePair)

    def test_attachments_built_with_proxy_urls(self):
        entity = self._make_hb_entity('77')

        hb_item = HbItem(api_dict={
            'id': '77',
            'attachments': [
                {
                    'id': 'att-1',
                    'title': 'Receipt',
                    'mimeType': 'image/png',
                    'thumbnail': {'id': 'thumb-1'},
                },
                {
                    # No thumbnail block at all.
                    'id': 'att-2',
                    'title': '',  # falls back to "Attachment att-2"
                    'mimeType': 'application/pdf',
                },
                {'id': ''},  # blank id, must be skipped
                'not-a-dict',
            ],
        })

        manager = Mock()
        manager.hb_client = Mock()
        manager.hb_client.api_url = 'http://homebox.example.com/api'
        manager.fetch_hb_item_from_api.return_value = hb_item
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxManager',
            return_value=manager,
        ):
            result = HomeBoxConnector().get_external_view_data(entity)

        self.assertIsInstance(result, StructuredViewData)
        self.assertEqual(len(result.attachments), 2)

        att1 = result.attachments[0]
        self.assertEqual(att1.id, 'att-1')
        self.assertEqual(att1.title, 'Receipt')
        self.assertEqual(att1.mime_type, 'image/png')
        # Proxy URLs route via the framework's services/homebox/ mount.
        self.assertIn(f'/{entity.id}/att-1', att1.open_url)
        self.assertIn(f'/{entity.id}/thumb-1', att1.thumbnail_url)

        att2 = result.attachments[1]
        self.assertEqual(att2.id, 'att-2')
        self.assertEqual(att2.title, 'Attachment att-2')
        self.assertEqual(att2.mime_type, 'application/pdf')
        self.assertIsNone(att2.thumbnail_url)
        self.assertIn(f'/{entity.id}/att-2', att2.open_url)

    def test_deep_link_url_strips_api_suffix(self):
        entity = self._make_hb_entity('500')

        manager = Mock()
        manager.hb_client = Mock()
        manager.hb_client.api_url = 'http://homebox.example.com/api'
        manager.fetch_hb_item_from_api.side_effect = RuntimeError('upstream down')
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxManager',
            return_value=manager,
        ):
            result = HomeBoxConnector().get_external_view_data(entity)

        self.assertEqual(result.deep_link_url, 'http://homebox.example.com/item/500')

    def test_deep_link_url_when_api_url_has_no_api_suffix(self):
        entity = self._make_hb_entity('600')

        manager = Mock()
        manager.hb_client = Mock()
        manager.hb_client.api_url = 'http://homebox.example.com'
        manager.fetch_hb_item_from_api.side_effect = RuntimeError('upstream down')
        manager.ensure_initialized = Mock()

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxManager',
            return_value=manager,
        ):
            result = HomeBoxConnector().get_external_view_data(entity)

        self.assertEqual(result.deep_link_url, 'http://homebox.example.com/item/600')

import logging
from unittest.mock import Mock, patch

import requests
from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.immich.enums import ImAttributeType
from hi.services.immich.im_client import ImmichClient, build_client
from hi.services.immich.im_metadata import ImmichMetaData


logging.disable(logging.CRITICAL)


def _make_attr(integration, attr_type, value):
    attr = IntegrationAttribute(
        integration = integration,
        name = attr_type.label,
        value = value,
        value_type_str = str(AttributeValueType.TEXT),
        attribute_type_str = 'PREDEFINED',
    )
    attr.integration_key = IntegrationKey(
        integration_id = ImmichMetaData.integration_id,
        integration_name = str(attr_type),
    )
    attr.save()
    return attr


class TestImmichClient(TestCase):

    def test_trailing_slash_normalized(self):
        c1 = ImmichClient(api_url = 'https://im.example.com', api_key = 'k')
        c2 = ImmichClient(api_url = 'https://im.example.com/', api_key = 'k')
        self.assertEqual(c1.api_url, 'https://im.example.com/')
        self.assertEqual(c2.api_url, 'https://im.example.com/')

    def test_api_key_carries_on_outbound_requests(self):
        # Verify the contract (every outbound request carries the
        # x-api-key) via Session.prepare_request rather than poking
        # the private session.headers dict.
        client = ImmichClient(api_url = 'https://im.example.com', api_key = 'abc')
        prepared = client._session.prepare_request(
            requests.Request('GET', 'https://im.example.com/api/probe'),
        )
        self.assertEqual(prepared.headers.get('x-api-key'), 'abc')

    def test_search_smart_posts_json_to_smart_endpoint(self):
        client = ImmichClient(api_url = 'https://im.example.com/', api_key = 'k')
        envelope = {'assets': {'items': [], 'total': 0, 'count': 0}}
        response = Mock()
        response.json.return_value = envelope
        response.raise_for_status = Mock()
        with patch.object(client._session, 'post', return_value = response) as mock_post:
            result = client.search_smart(query = 'sunset on the beach', size = 10)

        self.assertEqual(result, envelope)
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://im.example.com/api/search/smart')
        self.assertEqual(kwargs['json'], {'query': 'sunset on the beach', 'size': 10})

    def test_download_thumbnail_returns_bytes_and_mime(self):
        client = ImmichClient(api_url = 'https://im.example.com/', api_key = 'k')
        response = Mock()
        response.content = b'JPEG-BYTES'
        response.headers = {'Content-Type': 'image/jpeg'}
        response.raise_for_status = Mock()
        with patch.object(client._session, 'get', return_value = response) as mock_get:
            result = client.download_thumbnail(asset_id = 'abc-uuid')

        self.assertEqual(result, {'content': b'JPEG-BYTES', 'mime_type': 'image/jpeg'})
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], 'https://im.example.com/api/assets/abc-uuid/thumbnail')
        self.assertEqual(kwargs['params']['size'], 'thumbnail')

    def test_download_thumbnail_default_mime_when_missing(self):
        client = ImmichClient(api_url = 'https://im.example.com/', api_key = 'k')
        response = Mock()
        response.content = b'raw'
        response.headers = {}
        response.raise_for_status = Mock()
        with patch.object(client._session, 'get', return_value = response):
            result = client.download_thumbnail(asset_id = 'abc')
        self.assertEqual(result['mime_type'], 'application/octet-stream')

    def test_build_asset_web_url(self):
        client = ImmichClient(api_url = 'https://im.example.com/', api_key = 'k')
        self.assertEqual(
            client.build_asset_web_url(asset_id = 'abc-uuid'),
            'https://im.example.com/photos/abc-uuid',
        )


class TestBuildClient(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = ImmichMetaData.integration_id,
            is_enabled = True,
        )

    def test_returns_configured_client(self):
        _make_attr(self.integration, ImAttributeType.API_URL,
                   'https://immich.example.com')
        _make_attr(self.integration, ImAttributeType.API_KEY, 'abc')
        client = build_client()
        self.assertIsInstance(client, ImmichClient)
        self.assertEqual(client.api_url, 'https://immich.example.com/')
        self.assertEqual(client.api_key, 'abc')

    def test_no_integration_row_raises(self):
        Integration.objects.all().delete()
        with self.assertRaises(Integration.DoesNotExist):
            build_client()

    def test_disabled_integration_raises(self):
        self.integration.is_enabled = False
        self.integration.save()
        _make_attr(self.integration, ImAttributeType.API_URL,
                   'https://immich.example.com')
        _make_attr(self.integration, ImAttributeType.API_KEY, 'abc')
        with self.assertRaises(IntegrationAttributeError):
            build_client()

    def test_missing_attribute_raises(self):
        _make_attr(self.integration, ImAttributeType.API_URL,
                   'https://immich.example.com')
        # API_KEY deliberately omitted.
        with self.assertRaises(IntegrationAttributeError):
            build_client()

    def test_empty_attribute_value_raises(self):
        _make_attr(self.integration, ImAttributeType.API_URL,
                   'https://immich.example.com')
        _make_attr(self.integration, ImAttributeType.API_KEY, '   ')
        with self.assertRaises(IntegrationAttributeError):
            build_client()

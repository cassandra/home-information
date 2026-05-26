"""Tests for the paperless HTTP client and its factory.

The client is a thin requests wrapper; tests cover URL composition,
auth header, the documents-search + thumbnail-download calls, and
the trailing-slash forgiving normalization. The factory tests cover
the DB-driven config lookup, including the disabled-integration and
missing-attribute paths that should refuse to hand back a client.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.paperless.enums import PlAttributeType
from hi.services.paperless.pl_client import PaperlessClient, build_client
from hi.services.paperless.pl_metadata import PaperlessMetaData


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
        integration_id = PaperlessMetaData.integration_id,
        integration_name = str(attr_type),
    )
    attr.save()
    return attr


class TestPaperlessClient(TestCase):

    def test_trailing_slash_normalized(self):
        # The factory forgives operators who paste with or without a
        # trailing slash; both should yield the same upstream URLs.
        c1 = PaperlessClient(api_url = 'https://p.example.com', token = 't')
        c2 = PaperlessClient(api_url = 'https://p.example.com/', token = 't')
        self.assertEqual(c1.api_url, 'https://p.example.com/')
        self.assertEqual(c2.api_url, 'https://p.example.com/')

    def test_auth_header_set_on_session(self):
        client = PaperlessClient(api_url = 'https://p.example.com', token = 'abc')
        self.assertEqual(
            client._session.headers['Authorization'],
            'Token abc',
        )

    def test_search_documents_dispatches_and_returns_json(self):
        client = PaperlessClient(api_url = 'https://p.example.com/', token = 't')
        envelope = {'count': 2, 'results': [{'id': 1}, {'id': 2}]}
        response = Mock()
        response.json.return_value = envelope
        response.raise_for_status = Mock()
        with patch.object(client._session, 'get', return_value = response) as mock_get:
            result = client.search_documents(query = 'dishwasher', page_size = 50)

        self.assertEqual(result, envelope)
        args, kwargs = mock_get.call_args
        # URL composes against the normalized base.
        self.assertEqual(args[0], 'https://p.example.com/api/documents/')
        self.assertEqual(kwargs['params']['query'], 'dishwasher')
        self.assertEqual(kwargs['params']['page_size'], 50)

    def test_download_thumbnail_returns_bytes_and_mime(self):
        client = PaperlessClient(api_url = 'https://p.example.com/', token = 't')
        response = Mock()
        response.content = b'PNG-BYTES'
        response.headers = {'Content-Type': 'image/png'}
        response.raise_for_status = Mock()
        with patch.object(client._session, 'get', return_value = response) as mock_get:
            result = client.download_thumbnail(document_id = 42)

        self.assertEqual(result, {'content': b'PNG-BYTES', 'mime_type': 'image/png'})
        args, _ = mock_get.call_args
        self.assertEqual(args[0], 'https://p.example.com/api/documents/42/thumb/')

    def test_download_thumbnail_default_mime_when_missing(self):
        client = PaperlessClient(api_url = 'https://p.example.com/', token = 't')
        response = Mock()
        response.content = b'raw'
        response.headers = {}
        response.raise_for_status = Mock()
        with patch.object(client._session, 'get', return_value = response):
            result = client.download_thumbnail(document_id = 1)
        self.assertEqual(result['mime_type'], 'application/octet-stream')

    def test_build_document_details_url(self):
        client = PaperlessClient(api_url = 'https://p.example.com/', token = 't')
        self.assertEqual(
            client.build_document_details_url(document_id = 7),
            'https://p.example.com/documents/7/details/',
        )


class TestBuildClient(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = True,
        )

    def test_returns_configured_client(self):
        _make_attr(self.integration, PlAttributeType.API_URL,
                   'https://paperless.example.com')
        _make_attr(self.integration, PlAttributeType.API_TOKEN, 'abc')
        client = build_client()
        self.assertIsInstance(client, PaperlessClient)
        # Trailing slash normalized.
        self.assertEqual(client.api_url, 'https://paperless.example.com/')
        self.assertEqual(client.token, 'abc')

    def test_no_integration_row_raises(self):
        # Wipe the row created in setUp.
        Integration.objects.all().delete()
        with self.assertRaises(Integration.DoesNotExist):
            build_client()

    def test_disabled_integration_raises(self):
        self.integration.is_enabled = False
        self.integration.save()
        _make_attr(self.integration, PlAttributeType.API_URL,
                   'https://paperless.example.com')
        _make_attr(self.integration, PlAttributeType.API_TOKEN, 'abc')
        with self.assertRaises(IntegrationAttributeError):
            build_client()

    def test_missing_attribute_raises(self):
        _make_attr(self.integration, PlAttributeType.API_URL,
                   'https://paperless.example.com')
        # API_TOKEN deliberately omitted.
        with self.assertRaises(IntegrationAttributeError):
            build_client()

    def test_empty_attribute_value_raises(self):
        _make_attr(self.integration, PlAttributeType.API_URL,
                   'https://paperless.example.com')
        _make_attr(self.integration, PlAttributeType.API_TOKEN, '   ')
        with self.assertRaises(IntegrationAttributeError):
            build_client()

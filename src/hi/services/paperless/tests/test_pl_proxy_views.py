"""Tests for the paperless thumbnail proxy view.

Mirrors the HomeBox attachment-proxy test shape: unconfigured
integration → 404; upstream 404 → 404; other upstream failures →
502; success → 200 with passthrough bytes + content-type.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from requests import HTTPError, RequestException

from hi.integrations.exceptions import IntegrationAttributeError


logging.disable(logging.CRITICAL)


class TestThumbnailProxyView(TestCase):

    def _url(self, document_id: int = 1) -> str:
        return reverse(
            'paperless_thumbnail',
            kwargs = {'document_id': document_id},
        )

    @patch('hi.services.paperless.views.build_client',
           side_effect = IntegrationAttributeError('not configured'))
    def test_unconfigured_returns_404(self, _mock_build):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    @patch('hi.services.paperless.views.build_client')
    def test_successful_download_returns_bytes_and_mime(self, mock_build):
        client = Mock()
        client.download_thumbnail.return_value = {
            'content': b'PNG-BYTES',
            'mime_type': 'image/png',
        }
        mock_build.return_value = client

        response = self.client.get(self._url(document_id = 42))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'PNG-BYTES')
        self.assertEqual(response['Content-Type'], 'image/png')
        client.download_thumbnail.assert_called_once_with(document_id = 42)

    @patch('hi.services.paperless.views.build_client')
    def test_upstream_404_returns_404(self, mock_build):
        client = Mock()
        response = Mock()
        response.status_code = 404
        client.download_thumbnail.side_effect = HTTPError('404', response = response)
        mock_build.return_value = client

        result = self.client.get(self._url())
        self.assertEqual(result.status_code, 404)

    @patch('hi.services.paperless.views.build_client')
    def test_upstream_401_returns_502(self, mock_build):
        # Auth-level failures still get the bad-gateway treatment;
        # the browser sees "upstream trouble", not "doc missing".
        client = Mock()
        response = Mock()
        response.status_code = 401
        client.download_thumbnail.side_effect = HTTPError('401', response = response)
        mock_build.return_value = client

        result = self.client.get(self._url())
        self.assertEqual(result.status_code, 502)

    @patch('hi.services.paperless.views.build_client')
    def test_connection_error_returns_502(self, mock_build):
        client = Mock()
        client.download_thumbnail.side_effect = RequestException('boom')
        mock_build.return_value = client

        result = self.client.get(self._url())
        self.assertEqual(result.status_code, 502)

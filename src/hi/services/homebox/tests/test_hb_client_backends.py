"""Behavior tests for the HomeBox API client backends.

The public ``HbClient`` is a thin facade over a version-specific
backend (today: ``_HbLegacyBackend`` for the ``/v1/items`` API).
These tests exercise the backend directly — session ownership,
lazy login, retry-on-401, response-type handling, and the four
read methods.
"""

import logging
import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from requests import Response

from hi.services.homebox.hb_client import HbClient  # constants
from hi.services.homebox.hb_client_backends import _HbLegacyBackend


logging.disable(logging.CRITICAL)


class TestHbLegacyBackend(SimpleTestCase):

    def _api_options(self):
        return {
            HbClient.API_URL: 'https://homebox.local',
            HbClient.API_USER: 'user',
            HbClient.API_PASSWORD: 'pass',
        }

    def _response(self, status_code=200, json_data=None,
                  content_type='application/json', content=b''):
        response = Response()
        response.status_code = status_code
        response.headers['content-type'] = content_type

        if json_data is not None:
            response._content = json.dumps(json_data).encode('utf-8')
        else:
            response._content = content

        return response

    def test_init_strips_trailing_slash_and_defers_login(self):
        """Backend construction must not perform network I/O.
        ``_login`` is deferred to first request so a transient
        upstream problem at construction time does not leave the
        manager with a permanently null client."""
        with patch.object(_HbLegacyBackend, '_login') as mock_login:
            backend = _HbLegacyBackend(api_options={
                HbClient.API_URL: 'https://homebox.local/',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })

        self.assertEqual(backend.api_url, 'https://homebox.local')
        mock_login.assert_not_called()
        self.assertFalse(backend._authenticated)

    def test_make_request_lazy_logs_in_on_first_use(self):
        """First ``_make_request`` call performs the deferred login."""
        with patch.object(_HbLegacyBackend, '_login') as mock_login:
            backend = _HbLegacyBackend(api_options={
                HbClient.API_URL: 'https://homebox.local',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })

            success = self._response(status_code=200, json_data={'items': []})
            backend._session.request = Mock(return_value=success)

            # Simulate _login marking the backend as authenticated.
            def fake_login():
                backend._authenticated = True
            mock_login.side_effect = fake_login

            result = backend._make_request('GET', 'https://homebox.local/v1/items')

            mock_login.assert_called_once()
            self.assertEqual(result, {'items': []})

    def test_make_request_retries_after_unauthorized(self):
        with patch.object(_HbLegacyBackend, '_login') as mock_login:
            backend = _HbLegacyBackend(api_options={
                HbClient.API_URL: 'https://homebox.local',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })
            # Pretend a prior request already authenticated so we are
            # exercising only the 401 -> re-login -> retry path here.
            backend._authenticated = True

            unauthorized = self._response(status_code=401, json_data={'detail': 'Unauthorized'})
            success = self._response(status_code=200, json_data={'items': []})

            backend._session.request = Mock(side_effect=[unauthorized, success])

            result = backend._make_request('GET', 'https://homebox.local/v1/items')

        self.assertEqual(result, {'items': []})
        self.assertEqual(backend._session.request.call_count, 2)
        mock_login.assert_called_once()

    def test_make_request_returns_response_for_non_json_content(self):
        backend = _HbLegacyBackend(api_options=self._api_options())
        # Already-authenticated path so we exercise only the binary
        # attachment-download branch without triggering a lazy login.
        backend._authenticated = True

        binary_response = self._response(
            status_code=200,
            json_data=None,
            content_type='application/octet-stream',
            content=b'file-bytes',
        )
        backend._session.request = Mock(return_value=binary_response)

        result = backend._make_request('GET', 'https://homebox.local/v1/items/1/attachments/1')

        self.assertIs(result, binary_response)

    def test_get_items_summary_raises_when_response_is_not_json(self):
        """A non-JSON response on the items endpoint means the
        configured API URL is wrong; surface that as a clear
        ValueError instead of passing the raw Response through to
        ``get_items`` where it would explode on byte iteration."""
        backend = _HbLegacyBackend(api_options=self._api_options())
        backend._authenticated = True

        non_json_response = self._response(
            status_code=200,
            json_data=None,
            content_type='text/html',
            content=b'<html><body>not the API</body></html>',
        )
        backend._session.request = Mock(return_value=non_json_response)

        with self.assertRaises(ValueError) as context:
            backend.get_items_summary()
        self.assertIn('URL may be incorrect', str(context.exception))

    def test_get_items_fetches_detail_for_each_item(self):
        """Happy path: each summary entry fans out to a detail
        fetch and the detail responses are wrapped as HbItems.
        Items with no id are skipped (still safe — the summary
        is the only signal)."""
        with patch.object(_HbLegacyBackend, '_login'):
            backend = _HbLegacyBackend(api_options=self._api_options())

        backend._make_request = Mock(side_effect=[
            {'items': [{'id': 'item-1'}, {'id': 'item-2'}, {}, {'id': 'item-3'}]},
            {'id': 'item-1', 'name': 'One'},
            {'id': 'item-2', 'name': 'Two'},
            {'id': 'item-3', 'name': 'Three'},
        ])

        items = backend.get_items()

        self.assertEqual(len(items), 3)
        self.assertEqual([i.id for i in items], ['item-1', 'item-2', 'item-3'])

    def test_get_items_propagates_detail_fetch_failures(self):
        """A failed detail fetch propagates rather than being
        silently dropped: a partial-success outcome here is
        misinterpreted by the sync layer as upstream removals or a
        clean 'nothing to import,' which masks real upstream
        problems. The sync flow's outer try/except converts the
        propagated error into an ``error_list`` entry."""
        with patch.object(_HbLegacyBackend, '_login'):
            backend = _HbLegacyBackend(api_options=self._api_options())

        backend._make_request = Mock(side_effect=[
            {'items': [{'id': 'item-1'}, {'id': 'item-2'}]},
            {'id': 'item-1', 'name': 'One'},
            Exception('detail request failed'),
        ])

        with self.assertRaises(Exception) as context:
            backend.get_items()
        self.assertIn('detail request failed', str(context.exception))

    def test_get_item_returns_hb_item_from_detail_endpoint(self):
        with patch.object(_HbLegacyBackend, '_login'):
            backend = _HbLegacyBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value={'id': 'item-5', 'name': 'Five'})

        item = backend.get_item('item-5')

        self.assertEqual(item.id, 'item-5')
        self.assertEqual(item.name, 'Five')
        backend._make_request.assert_called_once_with(
            'GET',
            'https://homebox.local/v1/items/item-5',
        )

    def test_get_item_raises_when_response_is_not_dict(self):
        with patch.object(_HbLegacyBackend, '_login'):
            backend = _HbLegacyBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value=self._response(
            status_code=200,
            json_data=None,
            content_type='text/html',
            content=b'<html>not the api</html>',
        ))

        with self.assertRaises(ValueError) as context:
            backend.get_item('item-5')
        self.assertIn('non-JSON', str(context.exception))

    def test_download_attachment_returns_none_when_request_is_not_response(self):
        with patch.object(_HbLegacyBackend, '_login'):
            backend = _HbLegacyBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value={'content': 'wrong-type'})

        payload = backend.download_attachment(item_id='item-1', attachment_id='att-1')

        self.assertIsNone(payload)
        backend._make_request.assert_called_once_with(
            'GET',
            'https://homebox.local/v1/items/item-1/attachments/att-1',
        )

    def test_download_attachment_returns_content_and_mime_type(self):
        with patch.object(_HbLegacyBackend, '_login'):
            backend = _HbLegacyBackend(api_options=self._api_options())
        response = self._response(
            status_code=200,
            json_data=None,
            content_type='image/png',
            content=b'PNGDATA',
        )
        backend._make_request = Mock(return_value=response)

        payload = backend.download_attachment(item_id='item-1', attachment_id='att-1')

        self.assertEqual(payload, {
            'content': b'PNGDATA',
            'mime_type': 'image/png',
        })


class TestHbClientFacade(SimpleTestCase):
    """The public facade delegates every method to its backend.
    These tests pin the delegation contract independent of which
    backend is selected."""

    def _api_options(self):
        return {
            HbClient.API_URL: 'https://homebox.local',
            HbClient.API_USER: 'user',
            HbClient.API_PASSWORD: 'pass',
        }

    def test_facade_constructs_legacy_backend_today(self):
        # Phase 3 of #373 replaces this with a version probe;
        # today the facade always wires the legacy backend.
        client = HbClient(api_options=self._api_options())
        self.assertIsInstance(client._backend, _HbLegacyBackend)

    def test_facade_delegates_read_methods_to_backend(self):
        client = HbClient(api_options=self._api_options())
        client._backend = Mock()
        client._backend.get_items_summary.return_value = [{'id': '1'}]
        client._backend.get_item.return_value = Mock()
        client._backend.get_items.return_value = []
        client._backend.download_attachment.return_value = None

        client.get_items_summary()
        client.get_item('xyz')
        client.get_items()
        client.download_attachment('xyz', 'a1')

        client._backend.get_items_summary.assert_called_once_with()
        client._backend.get_item.assert_called_once_with('xyz')
        client._backend.get_items.assert_called_once_with()
        client._backend.download_attachment.assert_called_once_with('xyz', 'a1')

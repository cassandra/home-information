import logging
import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from requests import Response

from hi.services.homebox.hb_client import HbClient


logging.disable(logging.CRITICAL)


class TestHbClient(SimpleTestCase):

    def _api_options(self):
        return {
            HbClient.API_URL: 'https://homebox.local',
            HbClient.API_USER: 'user',
            HbClient.API_PASSWORD: 'pass',
        }

    def _response(self, status_code=200, json_data=None, content_type='application/json', content=b''):
        response = Response()
        response.status_code = status_code
        response.headers['content-type'] = content_type

        if json_data is not None:
            response._content = json.dumps(json_data).encode('utf-8')
        else:
            response._content = content

        return response

    def test_init_strips_trailing_slash_and_defers_login(self):
        """Client construction must not perform network I/O. _login is
        deferred to first request so a transient upstream problem at
        construction time does not leave the manager with a permanently
        null client."""
        with patch.object(HbClient, '_login') as mock_login:
            client = HbClient(api_options={
                HbClient.API_URL: 'https://homebox.local/',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })

        self.assertEqual(client._api_url, 'https://homebox.local')
        mock_login.assert_not_called()
        self.assertFalse(client._authenticated)

    def test_make_request_lazy_logs_in_on_first_use(self):
        """First _make_request call performs the deferred login."""
        with patch.object(HbClient, '_login') as mock_login:
            client = HbClient(api_options={
                HbClient.API_URL: 'https://homebox.local',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })

            success = self._response(status_code=200, json_data={'items': []})
            client._session.request = Mock(return_value=success)

            # Simulate _login marking the client as authenticated.
            def fake_login():
                client._authenticated = True
            mock_login.side_effect = fake_login

            result = client._make_request('GET', 'https://homebox.local/v1/items')

            mock_login.assert_called_once()
            self.assertEqual(result, {'items': []})

    def test_make_request_retries_after_unauthorized(self):
        with patch.object(HbClient, '_login') as mock_login:
            client = HbClient(api_options={
                HbClient.API_URL: 'https://homebox.local',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })
            # Pretend a prior request already authenticated us so we are
            # exercising only the 401 -> re-login -> retry path here.
            client._authenticated = True

            unauthorized = self._response(status_code=401, json_data={'detail': 'Unauthorized'})
            success = self._response(status_code=200, json_data={'items': []})

            client._session.request = Mock(side_effect=[unauthorized, success])

            result = client._make_request('GET', 'https://homebox.local/v1/items')

        self.assertEqual(result, {'items': []})
        self.assertEqual(client._session.request.call_count, 2)
        mock_login.assert_called_once()

    def test_make_request_returns_response_for_non_json_content(self):
        client = HbClient(api_options=self._api_options())
        # Already-authenticated path so we exercise only the binary
        # attachment-download branch without triggering a lazy login.
        client._authenticated = True

        binary_response = self._response(
            status_code=200,
            json_data=None,
            content_type='application/octet-stream',
            content=b'file-bytes',
        )
        client._session.request = Mock(return_value=binary_response)

        result = client._make_request('GET', 'https://homebox.local/v1/items/1/attachments/1')

        self.assertIs(result, binary_response)

    def test_get_items_summary_raises_when_response_is_not_json(self):
        """A non-JSON response on the items endpoint means the configured
        API URL is wrong; surface that as a clear ValueError instead of
        passing the raw Response through to get_items where it would
        explode on byte iteration."""
        client = HbClient(api_options=self._api_options())
        client._authenticated = True

        non_json_response = self._response(
            status_code=200,
            json_data=None,
            content_type='text/html',
            content=b'<html><body>not the API</body></html>',
        )
        client._session.request = Mock(return_value=non_json_response)

        with self.assertRaises(ValueError) as context:
            client.get_items_summary()
        self.assertIn('URL may be incorrect', str(context.exception))

    def test_get_items_fetches_detail_for_each_item(self):
        """Happy path: each summary entry fans out to a detail
        fetch and the detail responses are wrapped as HbItems.
        Items with no id are skipped (still safe — the summary
        is the only signal)."""
        with patch.object(HbClient, '_login'):
            client = HbClient(api_options=self._api_options())

        client._make_request = Mock(side_effect=[
            {'items': [{'id': 'item-1'}, {'id': 'item-2'}, {}, {'id': 'item-3'}]},
            {'id': 'item-1', 'name': 'One'},
            {'id': 'item-2', 'name': 'Two'},
            {'id': 'item-3', 'name': 'Three'},
        ])

        items = client.get_items()

        self.assertEqual(len(items), 3)
        self.assertEqual([i.id for i in items], ['item-1', 'item-2', 'item-3'])

    def test_get_items_propagates_detail_fetch_failures(self):
        """A failed detail fetch propagates rather than being
        silently dropped: a partial-success outcome here is
        misinterpreted by the sync layer as upstream removals or a
        clean 'nothing to import,' which masks real upstream
        problems. The sync flow's outer try/except converts the
        propagated error into an ``error_list`` entry."""
        with patch.object(HbClient, '_login'):
            client = HbClient(api_options=self._api_options())

        client._make_request = Mock(side_effect=[
            {'items': [{'id': 'item-1'}, {'id': 'item-2'}]},
            {'id': 'item-1', 'name': 'One'},
            Exception('detail request failed'),
        ])

        with self.assertRaises(Exception) as context:
            client.get_items()
        self.assertIn('detail request failed', str(context.exception))

    def test_download_attachment_returns_none_when_request_is_not_response(self):
        with patch.object(HbClient, '_login'):
            client = HbClient(api_options=self._api_options())
        client._make_request = Mock(return_value={'content': 'wrong-type'})

        payload = client.download_attachment(item_id='item-1', attachment_id='att-1')

        self.assertIsNone(payload)
        client._make_request.assert_called_once_with(
            'GET',
            'https://homebox.local/v1/items/item-1/attachments/att-1',
        )

    def test_download_attachment_returns_content_and_mime_type(self):
        with patch.object(HbClient, '_login'):
            client = HbClient(api_options=self._api_options())
        response = self._response(
            status_code=200,
            json_data=None,
            content_type='image/png',
            content=b'PNGDATA',
        )
        client._make_request = Mock(return_value=response)

        payload = client.download_attachment(item_id='item-1', attachment_id='att-1')

        self.assertEqual(payload, {
            'content': b'PNGDATA',
            'mime_type': 'image/png',
        })

import logging
import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from requests import Response

from hi.services.homebox.hb_client import HbClient
from hi.services.homebox.hb_models import HbItem


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

    def test_init_strips_trailing_slash_and_logs_in_when_credentials_exist(self):
        with patch.object(HbClient, '_login') as mock_login:
            client = HbClient(api_options={
                HbClient.API_URL: 'https://homebox.local/',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })

        self.assertEqual(client._api_url, 'https://homebox.local')
        mock_login.assert_called_once()

    def test_make_request_retries_after_unauthorized(self):
        with patch.object(HbClient, '_login') as mock_login:
            client = HbClient(api_options={
                HbClient.API_URL: 'https://homebox.local',
                HbClient.API_USER: 'user',
                HbClient.API_PASSWORD: 'pass',
            })
            mock_login.reset_mock()

            unauthorized = self._response(status_code=401, json_data={'detail': 'Unauthorized'})
            success = self._response(status_code=200, json_data={'items': []})

            client._session.request = Mock(side_effect=[unauthorized, success])

            result = client._make_request('GET', 'https://homebox.local/v1/items')

        self.assertEqual(result, {'items': []})
        self.assertEqual(client._session.request.call_count, 2)
        mock_login.assert_called_once()

    def test_make_request_returns_response_for_non_json_content(self):
        with patch.object(HbClient, '_login'):
            client = HbClient(api_options=self._api_options())

        binary_response = self._response(
            status_code=200,
            json_data=None,
            content_type='application/octet-stream',
            content=b'file-bytes',
        )
        client._session.request = Mock(return_value=binary_response)

        result = client._make_request('GET', 'https://homebox.local/v1/items/1/attachments/1')

        self.assertIs(result, binary_response)

    def test_get_items_fetches_detail_and_skips_invalid_or_failed_items(self):
        with patch.object(HbClient, '_login'):
            client = HbClient(api_options=self._api_options())

        client._make_request = Mock(side_effect=[
            {'items': [{'id': 'item-1'}, {'id': 'item-2'}, {}, {'id': 'item-3'}]},
            {'id': 'item-1', 'name': 'One'},
            Exception('detail request failed'),
            {'id': 'item-3', 'name': 'Three'},
        ])

        items = client.get_items()

        self.assertEqual(len(items), 2)
        self.assertIsInstance(items[0], HbItem)
        self.assertIsInstance(items[1], HbItem)
        self.assertEqual(items[0].id, 'item-1')
        self.assertEqual(items[1].id, 'item-3')

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

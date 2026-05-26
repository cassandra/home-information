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
from hi.services.homebox.hb_client_backends import (
    _HbEntitiesBackend,
    _HbLegacyBackend,
    _normalize_entity,
)


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

    def test_login_wraps_connection_error_with_operator_hint(self):
        """A network failure at login surfaces as a
        ``ConnectionError`` whose message points the operator at
        the configured URL — this is the diagnostic that helps
        the operator distinguish 'HomeBox is down' from 'wrong
        URL configured'."""
        backend = _HbLegacyBackend(api_options=self._api_options())
        backend._session.post = Mock(side_effect=OSError('refused'))

        with self.assertRaises(ConnectionError) as context:
            backend._login()

        self.assertIn('Cannot connect to HomeBox', str(context.exception))
        self.assertIn(backend.api_url, str(context.exception))

    def test_login_rejects_non_json_response(self):
        """The login endpoint must reply with JSON; a non-JSON
        response means the configured API URL is pointing at a
        non-API surface (e.g., the HTML UI) and should surface
        a clear ``ValueError`` with the API-path hint."""
        backend = _HbLegacyBackend(api_options=self._api_options())
        backend._session.post = Mock(return_value=self._response(
            status_code=200,
            json_data=None,
            content_type='text/html',
            content=b'<html>not the api</html>',
        ))

        with self.assertRaises(ValueError) as context:
            backend._login()
        self.assertIn('API path', str(context.exception))

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

    def test_facade_construction_defers_backend_resolution(self):
        # Construction must not trigger network I/O. The version
        # probe (which selects between legacy and entities
        # backends) is performed lazily on the first method call.
        client = HbClient(api_options=self._api_options())
        self.assertIsNone(client._backend)

    def test_facade_delegates_read_methods_to_backend(self):
        client = HbClient(api_options=self._api_options())
        # Pre-seed the backend so the lazy probe doesn't run.
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


class TestNormalizeEntity(SimpleTestCase):
    """The entities backend renames ``parent`` to ``location`` and
    drops the ``entityType`` discriminator so downstream code
    consumes a single internal vocabulary regardless of HB version."""

    def test_parent_renamed_to_location(self):
        normalized = _normalize_entity({
            'id': 'e-1',
            'name': 'Drill',
            'parent': {'id': 'loc-garage', 'name': 'Garage'},
        })
        self.assertEqual(normalized['location'], {'id': 'loc-garage', 'name': 'Garage'})
        self.assertNotIn('parent', normalized)

    def test_entity_type_dropped(self):
        normalized = _normalize_entity({
            'id': 'e-1',
            'entityType': {'id': 'et-1', 'name': 'Item', 'isLocation': False},
        })
        self.assertNotIn('entityType', normalized)

    def test_other_fields_preserved(self):
        normalized = _normalize_entity({
            'id': 'e-1',
            'name': 'Drill',
            'description': 'Cordless drill',
            'quantity': 1,
            'tags': [{'id': 't-1', 'name': 'tools'}],
            'archived': False,
        })
        self.assertEqual(normalized['name'], 'Drill')
        self.assertEqual(normalized['description'], 'Cordless drill')
        self.assertEqual(normalized['quantity'], 1)
        self.assertEqual(normalized['tags'], [{'id': 't-1', 'name': 'tools'}])
        self.assertEqual(normalized['archived'], False)

    def test_source_dict_not_mutated(self):
        # The backend hands the normalized copy to HbItem; the
        # original response dict should remain untouched in case a
        # future caller wants to inspect raw v0.26 fields.
        source = {'id': 'e-1', 'parent': {'name': 'Garage'}, 'entityType': {}}
        _normalize_entity(source)
        self.assertIn('parent', source)
        self.assertIn('entityType', source)


class TestHbEntitiesBackend(SimpleTestCase):
    """v0.26 backend: pagination loop, response normalization,
    and the path-rename across the four read methods."""

    def _api_options(self):
        return {
            HbClient.API_URL: 'https://homebox.local',
            HbClient.API_USER: 'user',
            HbClient.API_PASSWORD: 'pass',
        }

    def _entity_dict(self, entity_id, name='X', location_name='Garage'):
        return {
            'id': entity_id,
            'name': name,
            'parent': {'id': f'loc-{location_name.lower()}', 'name': location_name},
            'entityType': {'id': 'et-item', 'name': 'Item', 'isLocation': False},
        }

    def test_get_items_summary_handles_sentinel_total(self):
        """Real HB and the simulator return ``total=-1`` /
        ``pageSize=-1`` when serving everything in one page; the
        loop should terminate after the first page in that case."""
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value={
            'page': -1,
            'pageSize': -1,
            'total': -1,
            'items': [self._entity_dict('e-1'), self._entity_dict('e-2')],
        })

        items = backend.get_items_summary()

        self.assertEqual(len(items), 2)
        # Normalized in-place: parent → location, entityType dropped.
        for item in items:
            self.assertIn('location', item)
            self.assertNotIn('parent', item)
            self.assertNotIn('entityType', item)
        self.assertEqual(backend._make_request.call_count, 1)

    def test_get_items_summary_loops_until_total_reached(self):
        """When the server gives a real ``total`` and pages, the
        loop fetches additional pages until the count is met."""
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        page1 = {
            'page': 1, 'pageSize': 2, 'total': 3,
            'items': [self._entity_dict('e-1'), self._entity_dict('e-2')],
        }
        page2 = {
            'page': 2, 'pageSize': 2, 'total': 3,
            'items': [self._entity_dict('e-3')],
        }
        backend._make_request = Mock(side_effect=[page1, page2])

        items = backend.get_items_summary()

        self.assertEqual([i['id'] for i in items], ['e-1', 'e-2', 'e-3'])
        self.assertEqual(backend._make_request.call_count, 2)

    def test_get_items_summary_breaks_on_empty_page(self):
        """Defensive: if the server promises more items than it
        delivers (empty page), the loop must terminate rather than
        spin forever."""
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        page1 = {
            'page': 1, 'pageSize': 2, 'total': 10,
            'items': [self._entity_dict('e-1')],
        }
        page2 = {
            'page': 2, 'pageSize': 2, 'total': 10,
            'items': [],
        }
        backend._make_request = Mock(side_effect=[page1, page2])

        items = backend.get_items_summary()

        self.assertEqual(len(items), 1)
        self.assertEqual(backend._make_request.call_count, 2)

    def test_get_item_hits_entities_path_and_normalizes(self):
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value=self._entity_dict('e-7', name='Drill'))

        item = backend.get_item('e-7')

        self.assertEqual(item.id, 'e-7')
        self.assertEqual(item.name, 'Drill')
        # Field rename: HbItem.location reads ``location`` from the
        # api_dict — present because the backend renamed parent.
        self.assertEqual(item.location['name'], 'Garage')
        backend._make_request.assert_called_once_with(
            'GET',
            'https://homebox.local/v1/entities/e-7',
        )

    def test_get_item_raises_on_non_dict_response(self):
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value=Response())
        with self.assertRaises(ValueError) as context:
            backend.get_item('e-7')
        self.assertIn('non-JSON', str(context.exception))

    def test_download_attachment_uses_entities_path(self):
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        response = Response()
        response.status_code = 200
        response.headers['content-type'] = 'image/png'
        response._content = b'PNGDATA'
        backend._make_request = Mock(return_value=response)

        payload = backend.download_attachment(item_id='e-1', attachment_id='att-1')

        self.assertEqual(payload['mime_type'], 'image/png')
        self.assertEqual(payload['content'], b'PNGDATA')
        backend._make_request.assert_called_once_with(
            'GET',
            'https://homebox.local/v1/entities/e-1/attachments/att-1',
        )

    def test_get_items_summary_raises_when_response_is_not_json(self):
        """Mirror of the legacy backend's defensive check — a
        non-JSON list response on /v1/entities signals a
        misconfigured API URL; surface a clear ValueError instead
        of letting the loop iterate over a raw Response."""
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        backend._make_request = Mock(return_value=Response())

        with self.assertRaises(ValueError) as context:
            backend.get_items_summary()
        self.assertIn('URL may be incorrect', str(context.exception))

    def test_get_items_fans_out_to_entities_detail_path(self):
        """``get_items`` is now shared on the base class, but its
        per-version contract is that the per-item detail fetches
        go to the version-specific URL. Pin that the entities
        backend routes detail fetches to /v1/entities/<id>."""
        with patch.object(_HbEntitiesBackend, '_login'):
            backend = _HbEntitiesBackend(api_options=self._api_options())
        backend._make_request = Mock(side_effect=[
            {
                'page': -1, 'pageSize': -1, 'total': -1,
                'items': [{'id': 'e-1'}, {'id': 'e-2'}],
            },
            {'id': 'e-1', 'name': 'One'},
            {'id': 'e-2', 'name': 'Two'},
        ])

        items = backend.get_items()

        self.assertEqual([i.id for i in items], ['e-1', 'e-2'])
        # Per-item fetches hit the entities path, not items.
        detail_calls = [c for c in backend._make_request.call_args_list
                        if c.args[0] == 'GET' and 'entities/' in c.args[1]]
        self.assertEqual(len(detail_calls), 2)
        self.assertIn(
            'https://homebox.local/v1/entities/e-1',
            [c.args[1] for c in detail_calls],
        )
        self.assertIn(
            'https://homebox.local/v1/entities/e-2',
            [c.args[1] for c in detail_calls],
        )

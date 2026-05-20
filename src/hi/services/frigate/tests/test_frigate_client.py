import json
import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from requests.exceptions import ConnectionError

from hi.services.frigate.frigate_client import FrigateClient

logging.disable( logging.CRITICAL )


def _mock_response( status_code = 200,
                    body         = '',
                    content_type = 'application/json' ) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.headers = { 'content-type': content_type }
    response.text = body
    return response


class TestFrigateClientInit( TestCase ):

    def test_init_strips_trailing_slash(self):
        client = FrigateClient( api_options = {
            FrigateClient.BASE_URL: 'http://frigate.local:5000/',
        })
        self.assertEqual( client.base_url, 'http://frigate.local:5000' )

    def test_init_without_base_url_raises(self):
        with self.assertRaises( ValueError ):
            FrigateClient( api_options = {} )

    def test_init_optional_auth_header_sets_authorization(self):
        client = FrigateClient( api_options = {
            FrigateClient.BASE_URL: 'http://frigate.local:5000',
            FrigateClient.AUTH_HEADER: 'Bearer abc',
        })
        self.assertEqual( client._headers.get( 'Authorization' ), 'Bearer abc' )

    def test_init_without_auth_header_omits_authorization(self):
        client = FrigateClient( api_options = {
            FrigateClient.BASE_URL: 'http://frigate.local:5000',
        })
        self.assertNotIn( 'Authorization', client._headers )


class TestFrigateClientPing( TestCase ):

    def setUp(self):
        self.client = FrigateClient( api_options = {
            FrigateClient.BASE_URL: 'http://frigate.local:5000',
        })

    def test_ping_returns_none_on_success(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response( body = '{"cameras": {}}' )
            self.assertIsNone( self.client.ping() )

    def test_ping_raises_on_non_2xx(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response(
                status_code = 500, body = 'Internal Server Error',
            )
            with self.assertRaises( ValueError ) as ctx:
                self.client.ping()
            self.assertIn( '500', str( ctx.exception ) )

    def test_ping_raises_on_html_content_type(self):
        """A 200 with HTML body means the configured URL points at the
        Frigate web UI rather than the API — surface clearly instead of
        letting JSON decode fail later."""
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response(
                content_type = 'text/html', body = '<html>not the API</html>',
            )
            with self.assertRaises( ValueError ) as ctx:
                self.client.ping()
            self.assertIn( 'URL may be incorrect', str( ctx.exception ) )

    def test_ping_raises_on_malformed_json(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response( body = 'not json {' )
            with self.assertRaises( ValueError ) as ctx:
                self.client.ping()
            self.assertIn( 'not valid JSON', str( ctx.exception ) )

    def test_ping_propagates_network_errors(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.side_effect = ConnectionError( 'Connection refused' )
            with self.assertRaises( ConnectionError ):
                self.client.ping()


class TestFrigateClientGetCameras( TestCase ):

    def setUp(self):
        self.client = FrigateClient( api_options = {
            FrigateClient.BASE_URL: 'http://frigate.local:5000',
        })

    def test_get_cameras_returns_empty_list_for_no_cameras(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response( body = '{"cameras": {}}' )
            self.assertEqual( self.client.get_cameras(), [] )

    def test_get_cameras_returns_one_per_map_entry(self):
        cameras_payload = {
            'cameras': {
                'front_yard': { 'enabled': True },
                'back_door': { 'enabled': True },
            },
        }
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response(
                body = json.dumps( cameras_payload ),
            )
            result = self.client.get_cameras()
            self.assertEqual( len( result ), 2 )
            names = { entry[ 'name' ] for entry in result }
            self.assertEqual( names, { 'front_yard', 'back_door' } )

    def test_get_cameras_preserves_per_camera_config(self):
        cameras_payload = {
            'cameras': {
                'front_yard': { 'enabled': True, 'extra': 'value' },
            },
        }
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response(
                body = json.dumps( cameras_payload ),
            )
            ( entry, ) = self.client.get_cameras()
            self.assertEqual( entry[ 'name' ], 'front_yard' )
            self.assertEqual(
                entry[ 'config' ], { 'enabled': True, 'extra': 'value' },
            )

    def test_get_cameras_raises_when_cameras_field_missing(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response( body = '{}' )
            with self.assertRaises( ValueError ) as ctx:
                self.client.get_cameras()
            self.assertIn( 'cameras', str( ctx.exception ) )

    def test_get_cameras_raises_when_cameras_field_wrong_type(self):
        with patch( 'hi.services.frigate.frigate_client.get' ) as mock_get:
            mock_get.return_value = _mock_response(
                body = '{"cameras": ["front_yard"]}',
            )
            with self.assertRaises( ValueError ):
                self.client.get_cameras()

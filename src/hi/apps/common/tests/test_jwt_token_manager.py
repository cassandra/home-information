import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json
import jwt
import logging
from unittest.mock import patch
import time

from django.test import TestCase

from waa.apps.common.jwt_token_manager import (
    JwtTokenError,
    JwtTokenAlgorithm,
    JwtTokenManager,
)

logging.disable(logging.CRITICAL)


class JwtTokenManagerTestCase(TestCase):

    def setUp(self):
        # Test keys generated with:
        #
        #   openssl ecparam -genkey -name prime256v1 -noout -out ec_private_key.pem
        
        self.TEST_PRIVATE_KEY_1 = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIEK/C1jPHfxm5lXj+tDt/P/EJFnp2xXsbeRc2urem2dRoAoGCCqGSM49
AwEHoUQDQgAEnLbLcrnQ07e4vc79TqD8D3APe+Bw/QTGl/RFC4SaZNYQuZnL0V5a
BrLFpdU80BGZg4RlrExqAzEtkgS0V8CBMw==
-----END EC PRIVATE KEY-----"""
        
        return
    
    def test_create_token__bad_issuer_id(self):

        manager = JwtTokenManager()
        
        for issuer_id in [ None, '', '   ' ]:
            with self.assertRaises( JwtTokenError ):
                manager.create_token(
                    issuer_id = issuer_id,
                    key_id = 'test_key_id',
                    private_key = self.TEST_PRIVATE_KEY_1,
                    audience = 'appstoreconnect-v1',
                    algorithm = JwtTokenAlgorithm.ES256,
                )
            continue
        return
    
    def test_create_token__bad_key_id(self):

        manager = JwtTokenManager()
        
        for key_id in [ None, '', '   ' ]:
            with self.assertRaises( JwtTokenError ):
                manager.create_token(
                    issuer_id = 'test_issuer',
                    key_id = key_id,
                    private_key = self.TEST_PRIVATE_KEY_1,
                    audience = 'appstoreconnect-v1',
                    algorithm = JwtTokenAlgorithm.ES256,
                )
            continue
        return
    
    def test_create_token__bad_private_key(self):

        manager = JwtTokenManager()
        
        for private_key in [ None, '', '   ', 'bogus' ]:
            with self.assertRaises( JwtTokenError ):
                manager.create_token(
                    issuer_id = 'test_issuer',
                    key_id = 'test_key_id',
                    private_key = private_key,
                    audience = 'appstoreconnect-v1',
                    algorithm = JwtTokenAlgorithm.ES256,
                )
            continue
        return
    
    def test_create_token__bad_audience(self):

        manager = JwtTokenManager()
        
        for audience in [ None, '', '   ' ]:
            with self.assertRaises( JwtTokenError ):
                manager.create_token(
                    issuer_id = 'test_issuer',
                    key_id = 'test_key_id',
                    private_key = self.TEST_PRIVATE_KEY_1,
                    audience = audience,
                    algorithm = JwtTokenAlgorithm.ES256,
                )
            continue
        return
    
    def test_create_token__bad_algorithm(self):

        manager = JwtTokenManager()
        
        for algorithm in [ None, '', '   ' ]:
            with self.assertRaises( JwtTokenError ):
                manager.create_token(
                    issuer_id = 'test_issuer',
                    key_id = 'test_key_id',
                    private_key = self.TEST_PRIVATE_KEY_1,
                    audience = 'appstoreconnect-v1',
                    algorithm = algorithm,
                )
            continue
        return
    
    
    @patch.object(JwtTokenManager, 'get_current_time_epoch_secs')
    def test_create_token__happy_path( self, mock_get_current_time ):
        current_time_epoch_secs = int(time.time())
        token_expiration_secs = 10 * 60

        mock_get_current_time.return_value = current_time_epoch_secs

        # Need a public key for verification check
        private_key = serialization.load_pem_private_key(
            self.TEST_PRIVATE_KEY_1.encode(),
            password = None,
            backend = default_backend()
        )
        public_key = private_key.public_key()

        expected_headers = {
            "alg": JwtTokenAlgorithm.ES256.header_name,
            "kid": 'test_key_id',
            "typ": "JWT",
        }
        expected_payload = {
            "iss": 'test_issuer_id',
            'iat': current_time_epoch_secs,
            "exp": current_time_epoch_secs + token_expiration_secs,
            "aud": 'appstoreconnect-v1',
            "bid": 'com.pomdp.wordsacrossamerica',
        }
        
        manager = JwtTokenManager()

        jwt_token = manager.create_token(
            issuer_id = expected_payload['iss'],
            key_id = expected_headers['kid'],
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = expected_payload['aud'],
            algorithm = JwtTokenAlgorithm.ES256,
            bundle_id = expected_payload['bid'],
            token_expiration_secs = token_expiration_secs,
        )

        ( encoded_header, encoded_payload, signature ) = jwt_token.split( '.' )

        decoded_header = base64.b64decode( encoded_header + "===" )  # Needs padding for multiple of 4
        decoded_payload = base64.b64decode( encoded_payload + "===" )  # Needs padding for multiple of 4

        decoded_header_json = json.loads( decoded_header )
        decoded_payload_json = json.loads( decoded_payload )
        
        self.assertEqual( expected_headers, decoded_header_json )
        self.assertEqual( expected_payload, decoded_payload_json )

        try:
            _ = jwt.decode(
                jwt_token,
                public_key,
                algorithms = [ JwtTokenAlgorithm.ES256.encoding_name ],
                audience = expected_payload['aud'],
            )
        except Exception:
            self.fail("Token signature could not be decoded.")
        
        return
    
    @patch.object(JwtTokenManager, 'get_current_time_epoch_secs')
    def test_get_token__happy_path( self, mock_get_current_time ):
        mock_get_current_time.return_value = 1234567890

        manager = JwtTokenManager()

        ##########
        # First make sure that tokens with randomness in algorithm are not
        # the same via create_token().

        jwt_token_1 = manager.create_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        jwt_token_2 = manager.create_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        self.assertNotEqual( jwt_token_1, jwt_token_2 )

        ##########
        # Now make sure that consecutive calls to get_token() return from
        # cache, (cache key does not depend on private key).
        
        jwt_token_1 = manager.get_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        jwt_token_2 = manager.get_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        self.assertEqual( jwt_token_1, jwt_token_2 )

        ##########
        # Change of issuer id should bust the CACHE

        jwt_token_2 = manager.get_token(
            issuer_id = 'test_issuer_2',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        self.assertNotEqual( jwt_token_1, jwt_token_2 )
        
        ##########
        # Change of key id should bust the CACHE

        jwt_token_2 = manager.get_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id_2',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        self.assertNotEqual( jwt_token_1, jwt_token_2 )
        
        ##########
        # Change of audience should bust the CACHE

        jwt_token_2 = manager.get_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v2',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        self.assertNotEqual( jwt_token_1, jwt_token_2 )

        ##########
        # Double check original params still getting cached result.

        jwt_token_2 = manager.get_token(
            issuer_id = 'test_issuer',
            key_id = 'test_key_id',
            private_key = self.TEST_PRIVATE_KEY_1,
            audience = 'appstoreconnect-v1',
            algorithm = JwtTokenAlgorithm.ES256,
        )
        self.assertEqual( jwt_token_1, jwt_token_2 )
        
        return
    

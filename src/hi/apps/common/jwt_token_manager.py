import jwt
import time

from cachetools import TTLCache

from waa.apps.common.enums import LabeledEnum
from waa.apps.common.singleton import Singleton


class JwtTokenError(Exception):
    pass


class JwtTokenAlgorithm(LabeledEnum):

    ES256 = (
        'ES256',
        'Elliptic Curve Digital Signature Algorithm with the P-256 curve and the SHA-256 hash function.',
        'ES256',
        'ES256',
    )
    HS256 = (
        'HS256',
        'HMAC using SHA-256',
        'HS256',
        'HS256',
    )
    
    def __init__( self,
                  label          : str,
                  description    : str,
                  header_name    : str,
                  encoding_name  : str ):
        super().__init__( label, description )
        self.header_name = header_name
        self.encoding_name = encoding_name
        return
    
    
class JwtTokenManager( Singleton ):

    TOKEN_CACHE_EXPIRY_SECS = 15 * 60  # Max is 20 min for Apple Connect Store API
    
    def __init_singleton__( self ):
        self._token_cache = TTLCache( maxsize=4,
                                      ttl = self.TOKEN_CACHE_EXPIRY_SECS )
        return
    
    def get_token( self,
                   issuer_id              : str,
                   key_id                 : str,
                   private_key            : str,
                   audience               : str,
                   algorithm              : JwtTokenAlgorithm,
                   bundle_id              : str                = None,
                   token_expiration_secs  : int                = 900 ):
        """ Uses cache version for creating token  """
        
        assert token_expiration_secs <= ( 20 * 60 )  # Max expiration time (20 minutes for Apple API)
        
        cache_key = f'{issuer_id}:{key_id}:{audience}:{algorithm}'
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]

        jwt_token = self.create_token(
            issuer_id = issuer_id,
            key_id = key_id,
            private_key = private_key,
            audience = audience,
            algorithm = algorithm,
            bundle_id = bundle_id,
            token_expiration_secs = token_expiration_secs,
        )
        self._token_cache[cache_key] = jwt_token
        return jwt_token

    def create_token( self,
                      issuer_id              : str,
                      key_id                 : str,
                      private_key            : str,
                      audience               : str,
                      algorithm              : JwtTokenAlgorithm,
                      bundle_id              : str                = None,
                      token_expiration_secs  : int                = 900 ):
        """ Non-cache version for creating token """
        
        assert token_expiration_secs <= ( 20 * 60 )  # Max expiration time (20 minutes for Apple API)
        
        if not issuer_id or not isinstance( issuer_id, str ) or issuer_id.isspace():
            raise JwtTokenError( 'Missing issuer id or wrong type.' )
        if not key_id or not isinstance( key_id, str ) or key_id.isspace():
            raise JwtTokenError( 'Missing key id or wrong type.' )
        if not private_key or not isinstance( private_key, str ) or private_key.isspace():
            raise JwtTokenError( 'Missing private key or wronmg type.' )
        if not audience or not isinstance( audience, str ) or audience.isspace():
            raise JwtTokenError( 'Missing audience or wrong type.' )
        if not algorithm or not isinstance( algorithm, JwtTokenAlgorithm ):
            raise JwtTokenError( 'Missing algorithm or wrong type.' )
                
        current_time_epoch_secs = self.get_current_time_epoch_secs()

        headers = {
            "alg": algorithm.header_name,
            "kid": key_id,
            "typ": "JWT",
        }
        payload = {
            "iss": issuer_id,
            'iat': current_time_epoch_secs,
            "exp": current_time_epoch_secs + token_expiration_secs,
            "aud": audience,
        }
        if bundle_id:
            payload['bid'] = bundle_id
            
        try:
            jwt_token = jwt.encode(
                payload,
                private_key,
                algorithm = algorithm.encoding_name,
                headers = headers,
            )
            return jwt_token
        except ValueError as ve:
            raise JwtTokenError( str(ve) )
        
    def get_current_time_epoch_secs(self):
        # Allows mocking for unit tests
        return int( time.time() )

    def clear_cache( self ):
        self._token_cache.clear()
        return



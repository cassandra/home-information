from datetime import datetime
from enum import Enum
import re

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string


class MagicCodeStatus(Enum):

    INVALID  = 0
    EXPIRED  = 1
    VALID    = 2
    

class MagicCodeGenerator:
    """ 
    Used to generate and validate one-time login codes for password-less logins.

    Uses sessions to store code to be validated from user input.

    Usage:
        Generate:
            magic_code_generator = MagicCodeGenerator()
            magic_code = magic_code_generator.make_magic_code( request )
            <email magic code to user>
            <show a form to user to accept magic code entry>

        Validate:
            magic_code = <user submits form with magic code they entered>
            magic_code_generator = MagicCodeGenerator()
            is_valid = magic_code_generator.check_magic_code( request, magic_code = magic_code )
            if is_valid:
                magic_code_generator.expire_magic_code( request )

    """

    MAGIC_CODE = 'magic_code'
    MAGIC_CODE_TIMESTAMP = 'magic_code_timestamp'

    MAGIC_CODE_TIMEOUT_SECS = settings.PASSWORD_RESET_TIMEOUT
    MAGIC_CODE_CHARS = 'abcdefhkpqrstwxy'
    MAGIC_CODE_LENGTH = 6
    
    BASE_DATETIME = timezone.make_aware( datetime(2001, 1, 1) )
    
    def make_magic_code( self, request ):

        magic_code = get_random_string( length = self.MAGIC_CODE_LENGTH,
                                        allowed_chars = self.MAGIC_CODE_CHARS )
        magic_code_origin_timestamp = self.get_elapsed_seconds()

        request.session[self.MAGIC_CODE] = magic_code
        request.session[self.MAGIC_CODE_TIMESTAMP] = magic_code_origin_timestamp
        
        return magic_code

    def check_magic_code( self, request, magic_code ) -> MagicCodeStatus:

        magic_code = re.sub( r'[\-\s]', '', magic_code )
        
        expected_magic_code = request.session.get( self.MAGIC_CODE )
        if magic_code != expected_magic_code:
            return MagicCodeStatus.INVALID
        
        magic_code_origin_timestamp = request.session.get( self.MAGIC_CODE_TIMESTAMP )
        current_timestamp = self.get_elapsed_seconds()
        timeout_secs = self.get_timeout_seconds()
        
        if ( current_timestamp - magic_code_origin_timestamp ) > timeout_secs:
            return MagicCodeStatus.EXPIRED

        return MagicCodeStatus.VALID

    def expire_magic_code( self, request ):
        request.session[self.MAGIC_CODE] = None
        request.session[self.MAGIC_CODE_TIMESTAMP] = None
        return

    @classmethod
    def get_elapsed_seconds(cls):
        return int(( cls.get_datetime_now() - cls.BASE_DATETIME ).total_seconds())

    @classmethod
    def get_datetime_now(cls):
        return timezone.now()
    
    @classmethod
    def get_timeout_seconds(cls):
        return cls.MAGIC_CODE_TIMEOUT_SECS
    

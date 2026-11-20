from datetime import datetime
from enum import Enum
import re
from typing import Optional

from django.utils import timezone
from django.utils.crypto import constant_time_compare, get_random_string

from .constants import UserConstants


class MagicCodeStatus(Enum):

    INVALID             = 0
    EXPIRED             = 1
    VALID               = 2
    TOO_MANY_ATTEMPTS   = 3
    NO_CODE             = 4
    

class MagicCodeGenerator:
    """
    Used to generate and redeem one-time login codes for password-less logins.

    Uses sessions to store the code to be validated from user input. A code is:
      - bound to the email address it was issued for;
      - single use: consumed when redeemed successfully;
      - short lived: expires after MAGIC_CODE_TIMEOUT_SECS;
      - limited to MAX_FAILED_ATTEMPTS wrong guesses before it is discarded.

    Redeeming with no code in the session (already used, discarded, or never
    issued) reports NO_CODE, as only a new code can succeed.

    Usage:
        Generate:
            magic_code = MagicCodeGenerator().make_magic_code( request, email_address = email_address )
            <email magic code to user>
            <show a form to user to accept magic code entry>

        Redeem:
            status = MagicCodeGenerator().redeem_magic_code( request,
                                                             email_address = email_address,
                                                             magic_code = magic_code )
            if status == MagicCodeStatus.VALID:
                <sign in the user>
    """

    MAGIC_CODE = 'magic_code'
    MAGIC_CODE_TIMESTAMP = 'magic_code_timestamp'
    MAGIC_CODE_EMAIL = 'magic_code_email'
    MAGIC_CODE_FAILED_ATTEMPTS = 'magic_code_failed_attempts'

    MAGIC_CODE_TIMEOUT_SECS = 15 * 60
    MAX_FAILED_ATTEMPTS = 5

    BASE_DATETIME = timezone.make_aware( datetime(2001, 1, 1) )

    def make_magic_code( self, request, email_address : str ) -> str:

        magic_code = get_random_string( length = UserConstants.MAGIC_CODE_KEYPAD.length,
                                        allowed_chars = UserConstants.MAGIC_CODE_KEYPAD.alphabet )

        request.session[self.MAGIC_CODE] = magic_code
        request.session[self.MAGIC_CODE_TIMESTAMP] = self.get_elapsed_seconds()
        request.session[self.MAGIC_CODE_EMAIL] = email_address
        request.session[self.MAGIC_CODE_FAILED_ATTEMPTS] = 0
        return magic_code

    def redeem_magic_code( self, request, email_address : str, magic_code : str ) -> MagicCodeStatus:
        """ Any outcome other than a wrong guess under the attempt limit consumes the code. """

        unusable_status = self.unusable_code_status( request )
        if unusable_status:
            self.expire_magic_code( request )
            return unusable_status

        if not self._matches( request,
                              expected_magic_code = request.session.get( self.MAGIC_CODE ),
                              email_address = email_address,
                              magic_code = magic_code ):
            return self._record_failed_attempt( request )

        self.expire_magic_code( request )
        return MagicCodeStatus.VALID

    def unusable_code_status( self, request ) -> Optional[ MagicCodeStatus ]:
        """ Why no code in the session can be redeemed (NO_CODE or EXPIRED), or None if one can. """
        if not request.session.get( self.MAGIC_CODE ):
            return MagicCodeStatus.NO_CODE
        elapsed_secs = self.get_elapsed_seconds() - request.session.get( self.MAGIC_CODE_TIMESTAMP )
        if elapsed_secs > self.get_timeout_seconds():
            return MagicCodeStatus.EXPIRED
        return None

    def expire_magic_code( self, request ):
        for key in ( self.MAGIC_CODE,
                     self.MAGIC_CODE_TIMESTAMP,
                     self.MAGIC_CODE_EMAIL,
                     self.MAGIC_CODE_FAILED_ATTEMPTS ):
            request.session.pop( key, None )
        return

    def _matches( self, request, expected_magic_code : str, email_address : str, magic_code : str ) -> bool:
        if email_address != request.session.get( self.MAGIC_CODE_EMAIL ):
            return False
        normalized_magic_code = re.sub( r'[\-\s]', '', magic_code ).lower()
        return constant_time_compare( normalized_magic_code, expected_magic_code.lower() )

    def _record_failed_attempt( self, request ) -> MagicCodeStatus:
        failed_attempts = request.session.get( self.MAGIC_CODE_FAILED_ATTEMPTS, 0 ) + 1
        if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            self.expire_magic_code( request )
            return MagicCodeStatus.TOO_MANY_ATTEMPTS
        request.session[self.MAGIC_CODE_FAILED_ATTEMPTS] = failed_attempts
        return MagicCodeStatus.INVALID

    @classmethod
    def get_timeout_minutes(cls):
        return cls.get_timeout_seconds() // 60

    @classmethod
    def get_elapsed_seconds(cls):
        return int(( cls.get_datetime_now() - cls.BASE_DATETIME ).total_seconds())

    @classmethod
    def get_datetime_now(cls):
        return timezone.now()
    
    @classmethod
    def get_timeout_seconds(cls):
        return cls.MAGIC_CODE_TIMEOUT_SECS
    

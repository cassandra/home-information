from dataclasses import dataclass, field
import logging
from typing import Dict

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User as UserType

from django.test import TestCase

import hi.apps.common.datetimeproxy as datetimeproxy


class BaseTestCase(TestCase):
    """
    Common testing utilties.
    """
    
    def setUp(self):
        # With the APPEND_SLASHES feature, you can see a lot of warnings as
        # it does its work to add/remove slashes.  We are not so interested
        # in seeing WARNING message during testing.
        #
        logger = logging.getLogger('django.request')
        self.previous_logger_level = logger.getEffectiveLevel()
        logger.setLevel(logging.ERROR)

        datetimeproxy.reset()

        self.async_http_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        }
        return


@dataclass
class MockSession(dict):

    session_key  : str   = None
    modified     : bool  = True
    
    def save(self):
        return

    def keys(self):
        return list()

    
@dataclass
class MockRequest:
    
    user               : UserType          = None
    GET                : Dict[str, str]    = field( default_factory = dict )
    POST               : Dict[str, str]    = field( default_factory = dict )
    META               : Dict[str, str]    = field( default_factory = dict )
    session            : Dict[str, str]    = field( default_factory = MockSession )
    game_context       : object            = None
    
    def __post_init__(self):
        if not self.user:
            self.user = AnonymousUser()
        return

    

from dataclasses import dataclass, field
import logging
from typing import Dict

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User as UserType
from django.test import TestCase, RequestFactory

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.view_parameters import ViewParameters
from hi.enums import ViewMode, ViewType


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

    def create_hi_request(self, method='GET', path='/test/', data=None, files=None,
                          view_mode: ViewMode = None, view_type: ViewType = None,
                          location_view_id: int = None, collection_id: int = None):
        """
        Create a properly configured test request with view_parameters attached.
        
        This simulates what ViewMiddleware does in real requests, ensuring that
        context processors and views have access to view_parameters.
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            path: Request path
            data: POST/GET data dictionary
            files: Files dictionary for file uploads (POST only)
            view_mode: ViewMode enum (defaults to ViewMode.default())
            view_type: ViewType enum (defaults to ViewType.default())
            location_view_id: Optional location view ID
            collection_id: Optional collection ID
            
        Returns:
            HttpRequest with view_parameters properly attached
        """
        # Create request using Django's RequestFactory for realism
        factory = RequestFactory()
        
        if method.upper() == 'GET':
            request = factory.get(path, data or {})
        elif method.upper() == 'POST':
            if files:
                # When files are present, pass both data and files to POST
                request = factory.post(path, data=data or {}, files=files)
            else:
                request = factory.post(path, data or {})
        elif method.upper() == 'PUT':
            request = factory.put(path, data or {})
        elif method.upper() == 'DELETE':
            request = factory.delete(path, data or {})
        else:
            request = factory.generic(method.upper(), path, data or {})
        
        # Set up session with view parameter data
        session = MockSession()
        if view_mode:
            session['view_mode'] = view_mode.name
        if view_type:
            session['view_type'] = view_type.name
        if location_view_id:
            session['location_view_id'] = str(location_view_id)
        if collection_id:
            session['collection_id'] = str(collection_id)
            
        request.session = session
        
        # CRUCIAL: Simulate what ViewMiddleware does - attach view_parameters
        request.view_parameters = ViewParameters.from_session(request)
        
        return request


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

    

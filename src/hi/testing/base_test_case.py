from dataclasses import dataclass, field
import logging
import tempfile
from contextlib import contextmanager
from typing import Dict
from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User as UserType
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile

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

    @contextmanager
    def isolated_media_root(self):
        """
        Context manager for isolated MEDIA_ROOT testing.
        
        Creates a temporary directory for MEDIA_ROOT to ensure tests don't
        pollute the production media directory with test files.
        
        Usage:
            with self.isolated_media_root() as temp_media:
                # Test file operations here
                # Files will be written to temp_media, not production MEDIA_ROOT
                pass
                # Temporary directory is automatically cleaned up
        """
        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                yield temp_media_root
    
    def create_test_text_file(self, filename='test_file.txt', content='test content'):
        """
        Create a test text file for file upload testing.
        
        Args:
            filename: Name of the file (default: 'test_file.txt')
            content: File content as string (default: 'test content')
            
        Returns:
            SimpleUploadedFile instance ready for testing
        """
        return SimpleUploadedFile(
            name=filename,
            content=content.encode('utf-8'),
            content_type='text/plain'
        )
    
    def create_test_image_file(self, filename='test_image.jpg'):
        """
        Create a test image file for file upload testing.
        
        Args:
            filename: Name of the image file (default: 'test_image.jpg')
            
        Returns:
            SimpleUploadedFile instance with minimal JPEG data
        """
        # Minimal valid JPEG header + data
        jpeg_data = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'
        )
        return SimpleUploadedFile(
            name=filename,
            content=jpeg_data,
            content_type='image/jpeg'
        )
    
    def create_test_pdf_file(self, filename='test_document.pdf'):
        """
        Create a test PDF file for file upload testing.
        
        Args:
            filename: Name of the PDF file (default: 'test_document.pdf')
            
        Returns:
            SimpleUploadedFile instance with minimal PDF data
        """
        # Minimal valid PDF content
        pdf_data = (
            b'%PDF-1.4\n'
            b'1 0 obj\n'
            b'<<\n'
            b'/Type /Catalog\n'
            b'/Pages 2 0 R\n'
            b'>>\n'
            b'endobj\n'
            b'2 0 obj\n'
            b'<<\n'
            b'/Type /Pages\n'
            b'/Kids [3 0 R]\n'
            b'/Count 1\n'
            b'>>\n'
            b'endobj\n'
            b'3 0 obj\n'
            b'<<\n'
            b'/Type /Page\n'
            b'/Parent 2 0 R\n'
            b'/MediaBox [0 0 612 792]\n'
            b'>>\n'
            b'endobj\n'
            b'xref\n'
            b'0 4\n'
            b'0000000000 65535 f \n'
            b'0000000010 00000 n \n'
            b'0000000053 00000 n \n'
            b'0000000125 00000 n \n'
            b'trailer\n'
            b'<<\n'
            b'/Size 4\n'
            b'/Root 1 0 R\n'
            b'>>\n'
            b'startxref\n'
            b'205\n'
            b'%%EOF\n'
        )
        return SimpleUploadedFile(
            name=filename,
            content=pdf_data,
            content_type='application/pdf'
        )
    
    def assert_file_exists_in_media(self, media_root, relative_path):
        """
        Assert that a file exists in the given media root.
        
        Args:
            media_root: The media root directory (usually from isolated_media_root)
            relative_path: The relative path to the file within media root
            
        Raises:
            AssertionError: If the file doesn't exist
        """
        import os
        full_path = os.path.join(media_root, relative_path)
        self.assertTrue( os.path.exists(full_path), 
                         f"File should exist in media root: {full_path}")
    
    def assert_file_content_matches(self, media_root, relative_path, expected_content):
        """
        Assert that a file in media root contains the expected content.
        
        Args:
            media_root: The media root directory (usually from isolated_media_root)
            relative_path: The relative path to the file within media root
            expected_content: The expected file content as bytes or string
            
        Raises:
            AssertionError: If content doesn't match
        """
        import os
        full_path = os.path.join(media_root, relative_path)
        
        with open(full_path, 'rb') as f:
            actual_content = f.read()
        
        if isinstance(expected_content, str):
            expected_content = expected_content.encode('utf-8')
            
        self.assertEqual( actual_content, expected_content,
                          f"File content should match for: {full_path}")

    def create_mock_requests_get(self, return_data=None, status_code=200, raise_for_status_error=None):
        """
        Create a properly configured mock for requests.get() that works with timeout protection.
        
        Args:
            return_data: Data to return from response.json()
            status_code: HTTP status code (default: 200)
            raise_for_status_error: Exception to raise from raise_for_status() if any
            
        Returns:
            Mock object configured to behave like requests.get
        """
        mock_response = Mock()
        mock_response.json.return_value = return_data or {}
        mock_response.status_code = status_code
        
        if raise_for_status_error:
            mock_response.raise_for_status.side_effect = raise_for_status_error
        else:
            mock_response.raise_for_status.return_value = None
        
        mock_get = Mock(return_value=mock_response)
        mock_get.__name__ = 'get'  # Required for external_api_mixin timeout logging
        
        return mock_get


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

    

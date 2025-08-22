from typing import Dict, Any, Optional
import json

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import Client

from hi.testing.base_test_case import BaseTestCase
from hi.enums import ViewType, ViewMode
from hi.apps.location.models import LocationView
from hi.apps.collection.models import Collection
from hi.view_parameters import ViewParameters


class ViewTestClient(Client):
    """Custom test client that ensures ViewMiddleware runs for each request."""
    
    def request(self, **request):
        response = super().request(**request)
        # The ViewMiddleware should be running, but let's ensure view_parameters
        # is set on the response's wsgi_request for test assertions
        if hasattr(response, 'wsgi_request') and not hasattr(response.wsgi_request, 'view_parameters'):
            response.wsgi_request.view_parameters = ViewParameters.from_session(response.wsgi_request)
        return response


class ViewTestBase(BaseTestCase):
    """
    Base class for all Django view tests, providing common utilities and assertions.
    """

    client_class = ViewTestClient

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def assertResponseStatusCode(self, response: HttpResponse, expected_code: int):
        """Assert that response has the expected status code."""
        self.assertEqual(
            response.status_code, 
            expected_code,
            f"Expected status code {expected_code}, got {response.status_code}"
        )

    def assertSuccessResponse(self, response: HttpResponse):
        """Assert that response has a 2xx status code."""
        self.assertTrue(
            200 <= response.status_code < 300,
            f"Expected 2xx status code, got {response.status_code}"
        )

    def assertErrorResponse(self, response: HttpResponse):
        """Assert that response has a 4xx status code."""
        self.assertTrue(
            400 <= response.status_code < 500,
            f"Expected 4xx status code, got {response.status_code}"
        )

    def assertServerErrorResponse(self, response: HttpResponse):
        """Assert that response has a 5xx status code."""
        self.assertTrue(
            500 <= response.status_code < 600,
            f"Expected 5xx status code, got {response.status_code}"
        )

    def assertHtmlResponse(self, response: HttpResponse):
        """Assert that response is HTML content type (status code independent)."""
        content_type = response.get('Content-Type', '').lower()
        self.assertTrue(
            'text/html' in content_type,
            f"Expected HTML content type, got '{content_type}'"
        )

    def assertJsonResponse(self, response: HttpResponse):
        """Assert that response is JSON content type (status code independent)."""
        content_type = response.get('Content-Type', '').lower()
        self.assertTrue(
            'application/json' in content_type,
            f"Expected JSON content type, got '{content_type}'"
        )

    def assertTemplateRendered(self, response: HttpResponse, template_name: str):
        """Assert that the specified template was used to render the response."""
        template_names = [t.name for t in response.templates]
        self.assertIn(
            template_name, 
            template_names,
            f"Template '{template_name}' not found in rendered templates: {template_names}"
        )

    def assertSessionValue(self, response: HttpResponse, key: str, expected_value):
        """Assert that a session value matches the expected value."""
        session = response.wsgi_request.session
        actual_value = session.get(key)
        self.assertEqual(
            actual_value,
            expected_value,
            f"Session key '{key}': expected '{expected_value}', got '{actual_value}'"
        )

    def assertSessionContains(self, response: HttpResponse, key: str):
        """Assert that a session contains the specified key."""
        session = response.wsgi_request.session
        self.assertIn(
            key,
            session,
            f"Session key '{key}' not found in session keys: {list(session.keys())}"
        )

    def assertRedirectsToTemplates(self, initial_url: str, expected_templates: list):
        """Assert that URL redirects and final response renders all expected templates."""
        response = self.client.get(initial_url, follow=True)
        
        self.assertTrue(
            len(response.redirect_chain) > 0,
            f"Expected redirect from {initial_url}, but got direct response"
        )
        
        self.assertSuccessResponse(response)
        for template in expected_templates:
            self.assertTemplateRendered(response, template)
        return response

    # Session Management Convenience Methods
    
    def setSessionViewType(self, view_type: ViewType):
        """Set the view_type in the session for subsequent requests."""
        session = self.client.session
        session['view_type'] = str(view_type)
        session.save()
    
    def setSessionViewMode(self, view_mode: ViewMode):
        """Set the view_mode in the session for subsequent requests."""
        session = self.client.session
        session['view_mode'] = str(view_mode)
        session.save()
    
    def setSessionLocationView(self, location_view: Optional[LocationView]):
        """Set the location_view_id in the session for subsequent requests."""
        session = self.client.session
        session['location_view_id'] = location_view.id if location_view else None
        session.save()
    
    def setSessionCollection(self, collection: Optional[Collection]):
        """Set the collection_id in the session for subsequent requests."""
        session = self.client.session
        session['collection_id'] = collection.id if collection else None
        session.save()
    
    def setSessionViewParameters(self,
                                 view_type: Optional[ViewType] = None,
                                 view_mode: Optional[ViewMode] = None,
                                 location_view: Optional[LocationView] = None,
                                 collection: Optional[Collection] = None):
        """Convenience method to set multiple view parameters at once."""
        session = self.client.session
        if view_type is not None:
            session['view_type'] = str(view_type)
        if view_mode is not None:
            session['view_mode'] = str(view_mode)
        if location_view is not None:
            session['location_view_id'] = location_view.id
        if collection is not None:
            session['collection_id'] = collection.id
        session.save()


class SyncTestMixin:
    """
    Mixin providing synchronous testing capabilities.
    No special methods needed beyond base - regular client.get(), client.post() etc.
    """
    pass


class AsyncTestMixin:
    """
    Mixin providing asynchronous (AJAX) testing capabilities.
    Includes helper methods that automatically add AJAX headers.
    """

    def async_get(self, url: str, data: Dict[str, Any] = None) -> HttpResponse:
        """Make a GET request with AJAX headers."""
        return self.client.get(
            url, 
            data=data or {}, 
            **self.async_http_headers
        )

    def async_post(self, url: str, data: Dict[str, Any] = None) -> HttpResponse:
        """Make a POST request with AJAX headers."""
        return self.client.post(
            url, 
            data=data or {}, 
            **self.async_http_headers
        )

    def async_put(self, url: str, data: Dict[str, Any] = None) -> HttpResponse:
        """Make a PUT request with AJAX headers."""
        return self.client.put(
            url, 
            data=json.dumps(data or {}),
            content_type='application/json',
            **self.async_http_headers
        )

    def async_delete(self, url: str, data: Dict[str, Any] = None) -> HttpResponse:
        """Make a DELETE request with AJAX headers."""
        return self.client.delete(
            url, 
            data=json.dumps(data or {}),
            content_type='application/json',
            **self.async_http_headers
        )


class SyncViewTestCase(ViewTestBase, SyncTestMixin):
    """
    Test case for synchronous views (traditional Django page views and API endpoints).
    Uses regular client.get(), client.post() methods for testing.
    """
    pass


class AsyncViewTestCase(ViewTestBase, AsyncTestMixin):
    """
    Test case for asynchronous views (AJAX endpoints).
    Provides async_get(), async_post() methods that include AJAX headers.
    """
    pass


class DualModeViewTestCase(ViewTestBase, SyncTestMixin, AsyncTestMixin):
    """
    Test case for dual-mode views (HiModalView/HiGridView) that handle both
    synchronous and asynchronous requests.
    
    Provides both regular client methods (sync) and async_* methods (AJAX) 
    to test the same view in both contexts.
    """
    pass

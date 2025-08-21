import logging
from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from custom.models import CustomUser
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import ResolverMatch

from hi.apps.user.middleware import AuthenticationMiddleware
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAuthenticationMiddleware(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse('success'))
        self.middleware = AuthenticationMiddleware(self.get_response)
        
        self.authenticated_user = CustomUser.objects.create_user(
            email='auth@example.com',
            password='authpass'
        )

    def test_middleware_initialization(self):
        """Test AuthenticationMiddleware initializes correctly."""
        middleware = AuthenticationMiddleware(self.get_response)
        
        self.assertEqual(middleware.get_response, self.get_response)
        
        # Verify exempt URL names are defined
        expected_exempt_urls = {
            'admin',
            'user_signin',
            'user_signin_magic_code',
            'user_signin_magic_link',
        }
        self.assertEqual(middleware.EXEMPT_VIEW_URL_NAMES, expected_exempt_urls)

    @override_settings(SUPPRESS_AUTHENTICATION=True)
    def test_middleware_bypasses_when_suppress_authentication_enabled(self):
        """Test middleware bypasses authentication when SUPPRESS_AUTHENTICATION is True."""
        request = self.factory.get('/some-protected-path')
        request.user = AnonymousUser()
        
        with patch('hi.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='protected_view', app_name='main')
            
            response = self.middleware(request)
            
            # Should call get_response directly without authentication check
            self.get_response.assert_called_once_with(request)
            self.assertEqual(response, self.get_response.return_value)

    def test_middleware_bypasses_when_user_authenticated(self):
        """Test middleware bypasses when user is already authenticated."""
        request = self.factory.get('/some-protected-path')
        request.user = self.authenticated_user
        
        with patch('hi.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='protected_view', app_name='main')
            
            response = self.middleware(request)
            
            # Should call get_response directly without authentication check
            self.get_response.assert_called_once_with(request)
            self.assertEqual(response, self.get_response.return_value)

    def test_middleware_allows_admin_app_access(self):
        """Test middleware allows access to admin app without authentication."""
        request = self.factory.get('/admin/some-admin-path')
        request.user = AnonymousUser()
        
        with patch('hi.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='admin_view', app_name='admin')
            
            response = self.middleware(request)
            
            # Should call get_response directly for admin app
            self.get_response.assert_called_once_with(request)
            self.assertEqual(response, self.get_response.return_value)

    def test_middleware_allows_exempt_signin_urls(self):
        """Test middleware allows access to exempt signin URLs."""
        exempt_urls = [
            'user_signin',
            'user_signin_magic_code', 
            'user_signin_magic_link'
        ]
        
        for url_name in exempt_urls:
            with self.subTest(url_name=url_name):
                request = self.factory.get(f'/{url_name}')
                request.user = AnonymousUser()
                
                with patch('hi.apps.user.middleware.resolve') as mock_resolve:
                    mock_resolve.return_value = Mock(url_name=url_name, app_name='user')
                    
                    response = self.middleware(request)
                    
                    # Should call get_response directly for exempt URLs
                    self.get_response.assert_called_once_with(request)
                    self.assertEqual(response, self.get_response.return_value)
                    
                # Reset mock for next iteration
                self.get_response.reset_mock()

    @patch('hi.apps.user.middleware.UserSigninView')
    @override_settings(SUPPRESS_AUTHENTICATION=False)
    def test_middleware_redirects_unauthenticated_non_exempt_requests(self, mock_signin_view_class):
        """Test middleware redirects unauthenticated users to signin for non-exempt URLs."""
        mock_signin_view = Mock()
        mock_signin_response = HttpResponse('signin page')
        mock_signin_view.get.return_value = mock_signin_response
        mock_signin_view_class.return_value = mock_signin_view
        
        request = self.factory.get('/protected-view')
        request.user = AnonymousUser()
        
        with patch('hi.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='protected_view', app_name='main')
            
            response = self.middleware(request)
            
            # Should create UserSigninView and call get method
            mock_signin_view_class.assert_called_once()
            mock_signin_view.get.assert_called_once_with(request)
            self.assertEqual(response, mock_signin_response)
            
            # Should NOT call the original get_response
            self.get_response.assert_not_called()

    @override_settings(SUPPRESS_AUTHENTICATION=False)
    def test_middleware_handles_url_resolution_correctly(self):
        """Test middleware correctly resolves URLs and extracts app_name and url_name."""
        request = self.factory.get('/test/path')
        request.user = AnonymousUser()
        
        test_resolver_match = ResolverMatch(
            func=Mock(),
            args=(),
            kwargs={},
            url_name='test_view',
            app_names=['test_app'],
            namespaces=['test_app']
        )
        
        with patch('hi.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = test_resolver_match
            
            with patch('hi.apps.user.middleware.UserSigninView') as mock_signin_view_class:
                mock_signin_view = Mock()
                mock_signin_view.get.return_value = HttpResponse('signin')
                mock_signin_view_class.return_value = mock_signin_view
                
                self.middleware(request)
                
                # Verify resolve was called with correct path
                mock_resolve.assert_called_once_with(request.path)

    @override_settings(SUPPRESS_AUTHENTICATION=False)
    def test_middleware_respects_suppress_authentication_setting(self):
        """Test middleware respects SUPPRESS_AUTHENTICATION setting when False."""
        request = self.factory.get('/protected-view')
        request.user = AnonymousUser()
        
        with patch('hi.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='protected_view', app_name='main')
            
            with patch('hi.apps.user.middleware.UserSigninView') as mock_signin_view_class:
                mock_signin_view = Mock()
                mock_signin_view.get.return_value = HttpResponse('signin')
                mock_signin_view_class.return_value = mock_signin_view
                
                self.middleware(request)
                
                # Should redirect to signin when SUPPRESS_AUTHENTICATION=False
                mock_signin_view_class.assert_called_once()
                mock_signin_view.get.assert_called_once_with(request)

    def test_middleware_exempt_urls_are_comprehensive(self):
        """Test middleware exempt URLs cover all necessary authentication endpoints."""
        exempt_urls = self.middleware.EXEMPT_VIEW_URL_NAMES
        
        # Verify critical authentication URLs are exempt
        self.assertIn('user_signin', exempt_urls)
        self.assertIn('user_signin_magic_code', exempt_urls)
        self.assertIn('user_signin_magic_link', exempt_urls)
        self.assertIn('admin', exempt_urls)
        
        # Verify the set is not empty and contains strings
        self.assertTrue(len(exempt_urls) > 0)
        self.assertTrue(all(isinstance(url, str) for url in exempt_urls))

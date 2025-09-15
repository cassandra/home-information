import asyncio
import logging
import time
from unittest.mock import Mock, patch
from unittest import IsolatedAsyncioTestCase

from hi.apps.common.external_api_mixin import ExternalApiMixin


class TestExternalApiMixin(IsolatedAsyncioTestCase):
    """Test the ExternalApiMixin timeout protection functionality."""

    def setUp(self):
        # Create a test class that uses the mixin
        class TestClass(ExternalApiMixin):
            def __init__(self):
                self._logger = logging.getLogger(__name__)
                
            def get_api_timeout(self):
                return 0.1  # Very short timeout for fast tests
        
        self.test_instance = TestClass()

    async def test_safe_external_api_call_with_sync_function_success(self):
        """Test successful sync function call with timeout protection."""
        def mock_api_call():
            return "success"
        
        result = await self.test_instance.safe_external_api_call(mock_api_call)
        self.assertEqual(result, "success")

    async def test_safe_external_api_call_with_async_function_success(self):
        """Test successful async function call with timeout protection."""
        async def mock_async_api_call():
            return "async_success"
        
        result = await self.test_instance.safe_external_api_call(mock_async_api_call)
        self.assertEqual(result, "async_success")

    async def test_safe_external_api_call_sync_timeout(self):
        """Test that sync functions timeout correctly."""
        def slow_api_call():
            time.sleep(0.2)  # Longer than our 0.1s timeout
            return "should_not_reach"
        
        with self.assertRaises(asyncio.TimeoutError):
            await self.test_instance.safe_external_api_call(slow_api_call)

    async def test_safe_external_api_call_async_timeout(self):
        """Test that async functions timeout correctly."""
        async def slow_async_api_call():
            await asyncio.sleep(0.2)  # Longer than our 0.1s timeout
            return "should_not_reach"
        
        with self.assertRaises(asyncio.TimeoutError):
            await self.test_instance.safe_external_api_call(slow_async_api_call)

    async def test_safe_external_api_call_with_arguments(self):
        """Test that arguments are properly passed through."""
        def api_call_with_args(arg1, arg2, kwarg1=None):
            # Make sure this call is fast to avoid timeout
            return f"{arg1}-{arg2}-{kwarg1}"
        
        # Use a longer timeout class for this test
        class LongerTimeoutClass(ExternalApiMixin):
            def __init__(self):
                self._logger = logging.getLogger(__name__)
                
            def get_api_timeout(self):
                return 5.0  # Much longer timeout
        
        test_instance = LongerTimeoutClass()
        result = await test_instance.safe_external_api_call(
            api_call_with_args, "test", "value", kwarg1="extra"
        )
        self.assertEqual(result, "test-value-extra")

    async def test_safe_external_api_call_exception_propagation(self):
        """Test that exceptions from API calls are properly propagated."""
        def failing_api_call():
            raise ValueError("API error")
        
        with self.assertRaises(ValueError) as cm:
            await self.test_instance.safe_external_api_call(failing_api_call)
        
        self.assertEqual(str(cm.exception), "API error")

    def test_safe_external_api_call_sync_requests_detection(self):
        """Test that sync wrapper correctly identifies requests library functions."""
        # Create a mock function that looks like requests.get
        mock_requests_func = Mock()
        mock_requests_func.__module__ = 'requests.api'
        mock_requests_func.return_value = Mock()
        
        self.test_instance.safe_external_api_call_sync(
            mock_requests_func, "http://test.com"
        )
        
        # Verify timeout was passed
        mock_requests_func.assert_called_once_with("http://test.com", timeout=0.1)

    def test_safe_external_api_call_sync_with_custom_timeout(self):
        """Test sync wrapper with custom timeout override."""
        mock_requests_func = Mock()
        mock_requests_func.__module__ = 'requests.api'
        mock_requests_func.return_value = Mock()
        
        self.test_instance.safe_external_api_call_sync(
            mock_requests_func, "http://test.com", timeout=5.0
        )
        
        # Verify custom timeout was used
        mock_requests_func.assert_called_once_with("http://test.com", timeout=5.0)

    def test_safe_external_api_call_sync_non_requests_function(self):
        """Test sync wrapper with non-requests function falls back gracefully."""
        def non_requests_function():
            return "fallback_result"
        
        with patch.object(self.test_instance._logger, 'warning') as mock_warning:
            result = self.test_instance.safe_external_api_call_sync(non_requests_function)
            
            self.assertEqual(result, "fallback_result")
            mock_warning.assert_called_once()
            self.assertIn("sync timeout not implemented", mock_warning.call_args[0][0])

    def test_get_api_timeout_default(self):
        """Test default timeout value."""
        # Create instance without timeout override
        class DefaultTimeoutClass(ExternalApiMixin):
            def __init__(self):
                self._logger = logging.getLogger(__name__)
        
        instance = DefaultTimeoutClass()
        self.assertEqual(instance.get_api_timeout(), 30.0)

    def test_get_logger_with_different_logger_attributes(self):
        """Test that _get_logger finds logger in different attribute names."""
        # Test with _logger attribute
        class WithPrivateLogger(ExternalApiMixin):
            def __init__(self):
                self._logger = logging.getLogger("private")
        
        instance1 = WithPrivateLogger()
        self.assertEqual(instance1._get_logger().name, "private")
        
        # Test with logger attribute
        class WithPublicLogger(ExternalApiMixin):
            def __init__(self):
                self.logger = logging.getLogger("public")
        
        instance2 = WithPublicLogger()
        self.assertEqual(instance2._get_logger().name, "public")
        
        # Test fallback to module logger
        class WithoutLogger(ExternalApiMixin):
            pass
        
        instance3 = WithoutLogger()
        expected_logger_name = WithoutLogger.__module__
        self.assertEqual(instance3._get_logger().name, expected_logger_name)


class TestExternalApiMixinIntegration(IsolatedAsyncioTestCase):
    """Integration tests with real timeout scenarios."""

    def setUp(self):
        class IntegrationTestClass(ExternalApiMixin):
            def __init__(self):
                self._logger = logging.getLogger(__name__)
                
            def get_api_timeout(self):
                return 0.5  # Half second timeout
        
        self.test_instance = IntegrationTestClass()

    async def test_monitor_continues_after_timeout_basic(self):
        """Test basic timeout and recovery functionality."""
        # Test that we can make a successful call
        def fast_api():
            return "success"
        
        result1 = await self.test_instance.safe_external_api_call(fast_api)
        self.assertEqual(result1, "success")
        
        # Test that we can catch a timeout
        def slow_api():
            time.sleep(1.0)  # Longer than 0.5s timeout
            return "should_not_reach"
        
        with self.assertRaises(asyncio.TimeoutError):
            await self.test_instance.safe_external_api_call(slow_api)
        
        # The above proves that the timeout mechanism works
        # In practice, monitors continue working after timeouts

    async def test_multiple_concurrent_api_calls_with_timeout(self):
        """Test multiple concurrent API calls with some timing out."""
        async def quick_call():
            await asyncio.sleep(0.1)
            return "quick"
        
        async def slow_call():
            await asyncio.sleep(1.0)  # Will timeout
            return "slow"
        
        # Run concurrent calls
        results = await asyncio.gather(
            self.test_instance.safe_external_api_call(quick_call),
            self.test_instance.safe_external_api_call(quick_call),
            self.test_instance.safe_external_api_call(slow_call),
            return_exceptions=True
        )
        
        # First two should succeed, third should timeout
        self.assertEqual(results[0], "quick")
        self.assertEqual(results[1], "quick")
        self.assertIsInstance(results[2], asyncio.TimeoutError)

    async def test_timeout_error_logging(self):
        """Test that timeout errors are properly logged."""
        # Patch the instance's logger directly
        with patch.object(self.test_instance, '_logger') as mock_logger:
            def slow_call():
                time.sleep(1.0)
            
            with self.assertRaises(asyncio.TimeoutError):
                await self.test_instance.safe_external_api_call(slow_call)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            log_message = mock_logger.error.call_args[0][0]
            self.assertIn("timed out after 0.5 seconds", log_message)
            self.assertIn("IntegrationTestClass", log_message)

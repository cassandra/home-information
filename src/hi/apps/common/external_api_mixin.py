import asyncio
import logging
from asgiref.sync import sync_to_async


class ExternalApiMixin:
    """
    Mixin providing timeout protection for external API calls.
    Can be used by any class that needs to make external API calls with timeout protection.
    """

    def get_api_timeout(self) -> float:
        """
        Get timeout for external API calls in seconds.
        Classes can override to provide custom timeouts.
        """
        return 30.0

    def _get_logger(self):
        """Get logger for this class. Override if logger is stored differently."""
        if hasattr(self, '_logger'):
            return self._logger
        elif hasattr(self, 'logger'):
            return self.logger
        else:
            return logging.getLogger(self.__class__.__module__)

    async def safe_external_api_call(self, api_func, *args, **kwargs):
        """
        Wrapper for external API calls with timeout protection and error handling.
        
        Args:
            api_func: The API function to call (sync or async)
            *args: Arguments to pass to the API function
            **kwargs: Keyword arguments to pass to the API function
            
        Returns:
            The result of the API call
            
        Raises:
            asyncio.TimeoutError: If the API call times out
            Exception: Any other exception from the API call
        """
        timeout = self.get_api_timeout()
        logger = self._get_logger()
        
        try:
            # Determine if the function is async or sync
            if asyncio.iscoroutinefunction(api_func):
                # Async function - call directly with timeout
                return await asyncio.wait_for(
                    api_func(*args, **kwargs),
                    timeout=timeout
                )
            else:
                # Sync function - wrap with sync_to_async and timeout
                return await asyncio.wait_for(
                    sync_to_async(api_func, thread_sensitive=True)(*args, **kwargs),
                    timeout=timeout
                )
        except asyncio.TimeoutError:
            logger.error(f'External API call timed out after {timeout} seconds in {self.__class__.__name__}')
            raise
        except Exception as e:
            logger.error(f'External API call failed in {self.__class__.__name__}: {e}')
            raise

    def safe_external_api_call_sync(self, api_func, *args, timeout=None, **kwargs):
        """
        Synchronous wrapper for external API calls with timeout protection.
        Useful for sync contexts like requests.get() calls.
        
        Args:
            api_func: The API function to call (must be sync)
            *args: Arguments to pass to the API function
            timeout: Optional timeout override
            **kwargs: Keyword arguments to pass to the API function
            
        Returns:
            The result of the API call
            
        Raises:
            requests.exceptions.Timeout: If the API call times out
            Exception: Any other exception from the API call
        """
        if timeout is None:
            timeout = self.get_api_timeout()
            
        logger = self._get_logger()
        
        try:
            # For requests library calls, pass timeout parameter
            if hasattr(api_func, '__module__') and 'requests' in str(api_func.__module__):
                return api_func(*args, timeout=timeout, **kwargs)
            else:
                # For other sync functions, we can't easily add timeout here
                # This would need to be handled at a higher level with threading
                func_name = getattr(api_func, '__name__', str(type(api_func).__name__))
                logger.warning(f'sync timeout not implemented for {func_name}, falling back to no timeout')
                return api_func(*args, **kwargs)
        except Exception as e:
            logger.error(f'External API call failed in {self.__class__.__name__}: {e}')
            raise

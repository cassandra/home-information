"""
Base class for singleton managers with async-safe initialization patterns.
"""

import asyncio
import logging
from abc import abstractmethod
from threading import Lock

from asgiref.sync import sync_to_async
from .singleton import Singleton

logger = logging.getLogger(__name__)


class SingletonManager(Singleton):
    """
    Base class for singleton managers that need both sync and async initialization.

    Provides thread-safe and async-safe initialization patterns with:
    - ensure_initialized() for sync contexts
    - ensure_initialized_async() for async contexts
    - reload() for sync reload (with threading.Lock)
    - reload_async() for async reload (with asyncio.Lock)

    Subclasses must implement:
    - _reload_implementation(): The actual reload logic (called with locks held)
    """

    def __init_singleton__(self):
        super().__init_singleton__()
        self._was_initialized = False
        self._data_lock = Lock()  # For sync contexts
        self._async_data_lock = asyncio.Lock()  # For async contexts

    @abstractmethod
    def _reload_implementation(self):
        """
        Perform the actual manager initialization/reload work.
        Called with appropriate locks already held.
        """
        pass

    def reload(self):
        """Reload manager configuration in sync context."""
        logger.debug(f'{self.__class__.__name__} loading started.')
        with self._data_lock:
            self._reload_implementation()
        logger.debug(f'{self.__class__.__name__} loading completed.')

    async def reload_async(self):
        """Reload manager configuration in async context."""
        logger.debug(f'{self.__class__.__name__} loading started (async).')
        async with self._async_data_lock:
            # Use sync_to_async for Django ORM operations in _reload_implementation
            await sync_to_async(self._reload_implementation, thread_sensitive=True)()
        logger.debug(f'{self.__class__.__name__} loading completed (async).')

    def ensure_initialized(self):
        """Thread-safe initialization for synchronous contexts."""
        if self._was_initialized:
            return
        with self._data_lock:
            # Double-check pattern
            if not self._was_initialized:
                self._reload_implementation()
                self._was_initialized = True

    async def ensure_initialized_async(self):
        """Async-safe initialization for asynchronous contexts."""
        if self._was_initialized:
            return
        async with self._async_data_lock:
            # Double-check pattern
            if not self._was_initialized:
                await sync_to_async(self._reload_implementation, thread_sensitive=True)()
                self._was_initialized = True
                

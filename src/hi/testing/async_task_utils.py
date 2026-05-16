"""
Utilities for testing async tasks and event loops.

This module provides cleanup utilities for Django tests that create
background event loops or async tasks, preventing test hangs.

Note: This is separate from AJAX/async request testing in view_test_base.py.
This module focuses on asyncio event loops and background tasks.
"""

import asyncio
import weakref
import logging
from django.test import TestCase, TransactionTestCase

logger = logging.getLogger(__name__)

# Global registry to track background event loops for test cleanup
_background_loops = weakref.WeakSet()
_background_threads = weakref.WeakSet()


def track_background_loop(loop):
    """
    Register a background event loop for cleanup tracking.
    Should be called by test classes that create event loops.
    """
    if loop:
        _background_loops.add(loop)


def track_background_thread(thread):
    """
    Register a background thread for cleanup tracking.
    Should be called by test classes that create background threads.
    """
    if thread:
        _background_threads.add(thread)


def stop_all_background_loops():
    """
    Stop all background event loops and threads. 
    Designed for test cleanup and shutdown.
    """
    loops_stopped = 0
    threads_joined = 0
    
    # Stop all registered event loops
    for loop in list(_background_loops):
        try:
            if loop and not loop.is_closed():
                if loop.is_running():
                    loop.call_soon_threadsafe(loop.stop)
                loops_stopped += 1
        except Exception as e:
            logger.debug(f"Error stopping background loop: {e}")
    
    # Wait for threads to finish (with timeout)
    for thread in list(_background_threads):
        try:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)  # 2 second timeout
                threads_joined += 1
        except Exception as e:
            logger.debug(f"Error joining background thread: {e}")
    
    if loops_stopped > 0 or threads_joined > 0:
        logger.debug(f"Stopped {loops_stopped} background loops and joined {threads_joined} threads")
    
    # Clear the registries
    _background_loops.clear()
    _background_threads.clear()


def get_background_loop_count():
    """
    Get the number of active background loops.
    Useful for testing and debugging.
    """
    active_loops = 0
    for loop in _background_loops:
        if loop and not loop.is_closed():
            active_loops += 1
    return active_loops


def get_background_thread_count():
    """
    Get the number of active background threads.
    Useful for testing and debugging.
    """
    active_threads = 0
    for thread in _background_threads:
        if thread and thread.is_alive():
            active_threads += 1
    return active_threads


class _AsyncLoopMixin:
    """Shared event-loop setUpClass/tearDownClass + run_async helper.
    Both AsyncTaskTestCase (TransactionTestCase-based) and
    AsyncTaskFastTestCase (TestCase-based) inherit it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._test_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls._test_loop)
        track_background_loop(cls._test_loop)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_test_loop'):
            try:
                if cls._test_loop.is_running():
                    cls._test_loop.call_soon_threadsafe(cls._test_loop.stop)
                if not cls._test_loop.is_closed():
                    cls._test_loop.close()
            except Exception as e:
                logger.debug(f"Error closing test loop: {e}")
        stop_all_background_loops()
        super().tearDownClass()

    def run_async(self, coro):
        if hasattr(self, '_test_loop'):
            return self._test_loop.run_until_complete(coro)
        else:
            return asyncio.run(coro)


class AsyncTaskTestCase(_AsyncLoopMixin, TransactionTestCase):
    """Async event-loop helper with TransactionTestCase semantics.
    Required when async code under test wraps DB queries via
    ``sync_to_async`` and the worker thread needs to see test
    setUp's writes (cross-connection visibility)."""


class AsyncTaskFastTestCase(_AsyncLoopMixin, TestCase):
    """Async event-loop helper with TestCase semantics. Faster
    (transaction rollback instead of per-test DB flush) but does
    NOT support cross-connection visibility — use only when the
    async code under test doesn't call DB via sync_to_async."""


def cleanup_all_async_resources():
    """
    Global cleanup function to be called at the end of test runs.
    This ensures no async resources are left hanging.
    
    Can be called from Django test runner teardown or test hooks.
    """
    stop_all_background_loops()
    
    # Additional cleanup: try to close any remaining open loops
    try:
        current_loop = asyncio.get_running_loop()
        if current_loop and not current_loop.is_closed():
            current_loop.close()
    except RuntimeError:
        # No running loop, which is fine
        pass
    
    logger.debug("Completed async resource cleanup")

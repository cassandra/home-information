import asyncio
import logging

from hi.testing.async_task_utils import AsyncTaskTestCase
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

logging.disable(logging.CRITICAL)


class ConcreteTestMonitor(PeriodicMonitor):
    """Concrete implementation of PeriodicMonitor for testing."""
    
    def __init__(self):
        super().__init__(id='test-monitor', interval_secs=1)
        self.do_work_called = 0
        self.initialize_called = False
        self.cleanup_called = False
        self.do_work_error = None  # Set to raise an error in do_work
    
    async def initialize(self):
        self.initialize_called = True
        await super().initialize()
    
    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'test_monitor',
            provider_name = 'Test Monitor',
            description = '',            
        )

    async def do_work(self):
        self.do_work_called += 1
        if self.do_work_error:
            raise self.do_work_error
    
    async def cleanup(self):
        self.cleanup_called = True
        await super().cleanup()


class TestPeriodicMonitor(AsyncTaskTestCase):
    """Test PeriodicMonitor async lifecycle and behavior.
    
    Uses AsyncTaskTestCase to avoid database locking issues with async code.
    """
    
    def setUp(self):
        super().setUp()
        self.monitor = ConcreteTestMonitor()
    
    def test_abstract_do_work_must_be_implemented(self):
        """Test that do_work() must be implemented by subclasses."""
        
        class IncompleteMonitor(PeriodicMonitor):
            def __init__(self):
                super().__init__(id='incomplete', interval_secs=1)
                
            @classmethod
            def get_provider_info(cls) -> ProviderInfo:
                return ProviderInfo(
                    provider_id = 'test_monitor',
                    provider_name = 'Test Monitor',
                    description = '',            
                )
        
        monitor = IncompleteMonitor()
        
        async def test_logic():
            with self.assertRaises(NotImplementedError):
                await monitor.do_work()
        
        self.run_async(test_logic())
    
    def test_monitor_initialization(self):
        """Test monitor initializes with correct properties."""
        self.assertEqual(self.monitor.id, 'test-monitor')
        self.assertEqual(self.monitor._query_interval_secs, 1)
        self.assertEqual(self.monitor._query_counter, 0)
        self.assertFalse(self.monitor.is_running)
    
    def test_start_sets_is_running_and_calls_initialize(self):
        """Test start() sets is_running and calls initialize()."""
        
        async def test_logic():
            # Start the monitor but stop it immediately
            task = asyncio.create_task(self.monitor.start())
            
            # Give it a moment to start
            await asyncio.sleep(0.01)
            
            # Verify initialization
            self.assertTrue(self.monitor.is_running)
            self.assertTrue(self.monitor.initialize_called)
            
            # Stop the monitor
            self.monitor.stop()
            await asyncio.sleep(0.01)
            
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.run_async(test_logic())
    
    def test_run_query_increments_counter_and_calls_do_work(self):
        """Test run_query() increments counter and calls do_work()."""
        
        async def test_logic():
            self.assertEqual(self.monitor._query_counter, 0)
            self.assertEqual(self.monitor.do_work_called, 0)
            
            await self.monitor.run_query()
            
            self.assertEqual(self.monitor._query_counter, 1)
            self.assertEqual(self.monitor.do_work_called, 1)
            
            await self.monitor.run_query()
            
            self.assertEqual(self.monitor._query_counter, 2)
            self.assertEqual(self.monitor.do_work_called, 2)
        
        self.run_async(test_logic())
    
    def test_run_query_handles_exceptions_in_do_work(self):
        """Test run_query() catches and logs exceptions from do_work()."""
        
        async def test_logic():
            self.monitor.do_work_error = ValueError("Test error")
            
            # Should not raise exception
            await self.monitor.run_query()
            
            # Counter should still increment
            self.assertEqual(self.monitor._query_counter, 1)
            self.assertEqual(self.monitor.do_work_called, 1)
        
        self.run_async(test_logic())
    
    def test_stop_sets_is_running_false(self):
        """Test stop() sets is_running to False."""
        
        async def test_logic():
            # Start the monitor
            task = asyncio.create_task(self.monitor.start())
            await asyncio.sleep(0.01)
            
            self.assertTrue(self.monitor.is_running)
            
            # Stop the monitor
            self.monitor.stop()
            
            self.assertFalse(self.monitor.is_running)
            
            # Give it time to stop
            await asyncio.sleep(0.01)
            
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.run_async(test_logic())
    
    def test_cleanup_called_on_normal_stop(self):
        """Test cleanup() is called when monitor stops normally."""
        
        async def test_logic():
            self.assertFalse(self.monitor.cleanup_called)
            
            # Start the monitor
            task = asyncio.create_task(self.monitor.start())
            await asyncio.sleep(0.01)
            
            # Stop it normally
            self.monitor.stop()
            await asyncio.sleep(0.01)
            
            # Cancel and wait for task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Cleanup should have been called
            self.assertTrue(self.monitor.cleanup_called)
        
        self.run_async(test_logic())
    
    def test_cleanup_called_on_cancellation(self):
        """Test cleanup() is called when monitor is cancelled."""
        
        async def test_logic():
            self.assertFalse(self.monitor.cleanup_called)
            
            # Start the monitor
            task = asyncio.create_task(self.monitor.start())
            await asyncio.sleep(0.01)
            
            # Cancel it directly
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Cleanup should have been called
            self.assertTrue(self.monitor.cleanup_called)
        
        self.run_async(test_logic())
    
    def test_force_wake_triggers_immediate_query(self):
        """Test force_wake() triggers immediate query execution."""
        
        async def test_logic():
            self.assertEqual(self.monitor.do_work_called, 0)
            
            await self.monitor.force_wake()
            
            self.assertEqual(self.monitor.do_work_called, 1)
            self.assertEqual(self.monitor._query_counter, 1)
        
        self.run_async(test_logic())
    
    def test_monitor_runs_periodically(self):
        """Test monitor runs do_work() periodically at specified interval."""
        
        async def test_logic():
            # Use a very short interval for testing
            fast_monitor = ConcreteTestMonitor()
            fast_monitor._query_interval_secs = 0.05  # 50ms
            
            # Start the monitor
            task = asyncio.create_task(fast_monitor.start())
            
            # Let it run for a bit (should complete 2-3 cycles)
            await asyncio.sleep(0.15)
            
            # Stop the monitor
            fast_monitor.stop()
            await asyncio.sleep(0.01)
            
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Should have run multiple times
            self.assertGreaterEqual(fast_monitor.do_work_called, 2)
            self.assertLessEqual(fast_monitor.do_work_called, 4)
        
        self.run_async(test_logic())
    
    def test_monitor_continues_after_do_work_error(self):
        """Test monitor continues running even after do_work() raises exception."""
        
        async def test_logic():
            fast_monitor = ConcreteTestMonitor()
            fast_monitor._query_interval_secs = 0.05  # 50ms
            
            # Set error for first call
            fast_monitor.do_work_error = ValueError("Test error")
            
            # Start the monitor
            task = asyncio.create_task(fast_monitor.start())
            
            # Let it run for first iteration
            await asyncio.sleep(0.06)
            
            # Clear the error
            fast_monitor.do_work_error = None
            
            # Let it run more
            await asyncio.sleep(0.06)
            
            # Stop the monitor
            fast_monitor.stop()
            await asyncio.sleep(0.01)
            
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Should have continued running despite error
            self.assertGreaterEqual(fast_monitor.do_work_called, 2)

        self.run_async(test_logic())

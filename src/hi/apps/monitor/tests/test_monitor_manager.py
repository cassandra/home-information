import asyncio
import logging
import threading
from unittest.mock import Mock, patch, MagicMock

from django.test import TransactionTestCase, override_settings

from hi.apps.monitor.monitor_manager import AppMonitorManager
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

logging.disable(logging.CRITICAL)


class TestMonitor1(PeriodicMonitor):
    """Test monitor for discovery."""
    def __init__(self):
        super().__init__(id='test-monitor-1', interval_secs=60)
    
    async def do_work(self):
        pass


class TestMonitor2(PeriodicMonitor):
    """Another test monitor for discovery."""
    def __init__(self):
        super().__init__(id='test-monitor-2', interval_secs=60)
    
    async def do_work(self):
        pass


class TestAppMonitorManager(TransactionTestCase):
    """Test AppMonitorManager singleton and async behavior.
    
    Uses TransactionTestCase for async compatibility.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a single shared event loop for all tests
        cls._test_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls._test_loop)
    
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_test_loop'):
            cls._test_loop.close()
        super().tearDownClass()
    
    def run_async(self, coro):
        """Helper to run async coroutines using the shared event loop."""
        return self._test_loop.run_until_complete(coro)
    
    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        AppMonitorManager._instances = {}
        self.manager = AppMonitorManager()
        # Reset initialization state
        self.manager._initialized = False
        self.manager._monitor_map = dict()
        
    def tearDown(self):
        # Clean up any running monitors
        async def cleanup():
            await self.manager.shutdown()
        self.run_async(cleanup())
        super().tearDown()
    
    def test_singleton_behavior(self):
        """Test AppMonitorManager implements singleton pattern correctly."""
        manager1 = AppMonitorManager()
        manager2 = AppMonitorManager()
        
        self.assertIs(manager1, manager2)
        self.assertIs(self.manager, manager1)
    
    def test_singleton_thread_safety(self):
        """Test singleton is thread-safe."""
        # Reset singleton
        AppMonitorManager._instances = {}
        
        managers = []
        errors = []
        
        def create_manager():
            try:
                manager = AppMonitorManager()
                managers.append(manager)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads that try to create managers
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_manager)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have no errors
        self.assertEqual(len(errors), 0)
        
        # All managers should be the same instance
        self.assertGreater(len(managers), 0)
        first_manager = managers[0]
        for manager in managers:
            self.assertIs(manager, first_manager)
    
    def test_initialization_only_happens_once(self):
        """Test initialize() only runs once even if called multiple times."""
        
        async def test_logic():
            # Ensure manager is not initialized
            self.assertFalse(self.manager._initialized)
            
            # Mock the discovery method
            with patch.object(self.manager, '_discover_periodic_monitors') as mock_discover:
                mock_discover.return_value = []
                
                # Initialize first time
                await self.manager.initialize(self._test_loop)
                self.assertTrue(self.manager._initialized)
                
                # Initialize multiple times more
                await self.manager.initialize(self._test_loop)
                await self.manager.initialize(self._test_loop)
                
                # Discovery should only be called once
                mock_discover.assert_called_once()
                
                # Should remain initialized
                self.assertTrue(self.manager._initialized)
        
        self.run_async(test_logic())
    
    def test_initialization_thread_safety(self):
        """Test initialization is thread-safe with concurrent calls."""
        
        async def test_logic():
            # Ensure fresh state
            self.assertFalse(self.manager._initialized)
            
            discovery_count = 0
            
            def mock_discover():
                nonlocal discovery_count
                discovery_count += 1
                return []
            
            with patch.object(self.manager, '_discover_periodic_monitors', mock_discover):
                # Create multiple concurrent initialization tasks
                tasks = []
                for _ in range(5):
                    task = asyncio.create_task(self.manager.initialize(self._test_loop))
                    tasks.append(task)
                
                # Wait for all to complete
                await asyncio.gather(*tasks)
                
                # Discovery should only happen once due to lock
                self.assertEqual(discovery_count, 1)
                self.assertTrue(self.manager._initialized)
        
        self.run_async(test_logic())
    
    @patch('hi.apps.monitor.monitor_manager.apps')
    @patch('hi.apps.monitor.monitor_manager.import_module_safe')
    def test_discover_periodic_monitors_finds_subclasses(self, mock_import, mock_apps):
        """Test _discover_periodic_monitors() finds PeriodicMonitor subclasses."""
        # Mock app configs
        mock_app1 = Mock()
        mock_app1.name = 'hi.apps.test_app1'
        
        mock_app2 = Mock()
        mock_app2.name = 'hi.apps.test_app2'
        
        mock_app3 = Mock()
        mock_app3.name = 'other.app'  # Should be skipped
        
        mock_apps.get_app_configs.return_value = [mock_app1, mock_app2, mock_app3]
        
        # Mock module imports
        mock_module1 = MagicMock()
        mock_module1.TestMonitor1 = TestMonitor1
        mock_module1.NotAMonitor = str  # Should be ignored
        
        mock_module2 = MagicMock()
        mock_module2.TestMonitor2 = TestMonitor2
        
        def import_side_effect(module_name):
            if module_name == 'hi.apps.test_app1.monitors':
                return mock_module1
            elif module_name == 'hi.apps.test_app2.monitors':
                return mock_module2
            return None
        
        mock_import.side_effect = import_side_effect
        
        # Discover monitors
        monitors = self.manager._discover_periodic_monitors()
        
        # Should find both test monitors
        self.assertEqual(len(monitors), 2)
        self.assertIn(TestMonitor1, monitors)
        self.assertIn(TestMonitor2, monitors)
    
    @patch('hi.apps.monitor.monitor_manager.apps')
    @patch('hi.apps.monitor.monitor_manager.import_module_safe')
    def test_discover_handles_import_errors_gracefully(self, mock_import, mock_apps):
        """Test discovery handles import errors without crashing."""
        mock_app = Mock()
        mock_app.name = 'hi.apps.broken_app'
        mock_apps.get_app_configs.return_value = [mock_app]
        
        # Simulate import error
        mock_import.side_effect = ImportError("Module not found")
        
        # Should not raise exception
        monitors = self.manager._discover_periodic_monitors()
        
        # Should return empty list
        self.assertEqual(monitors, [])
    
    @override_settings(DEBUG=True, SUPPRESS_MONITORS=True)
    def test_monitors_suppressed_in_debug_mode(self):
        """Test monitors are not started when SUPPRESS_MONITORS is True."""
        
        async def test_logic():
            # Create a mock monitor class that returns a configured instance
            mock_monitor_instance = Mock(spec=PeriodicMonitor)
            mock_monitor_instance.id = 'test-monitor'
            mock_monitor_instance.is_running = False
            mock_monitor_instance.start = Mock()
            
            mock_monitor_class = Mock(return_value=mock_monitor_instance)
            
            with patch.object(self.manager, '_discover_periodic_monitors') as mock_discover:
                mock_discover.return_value = [mock_monitor_class]
                
                await self.manager.initialize(self._test_loop)
                
                # Monitor should be registered but not started
                self.assertIn('test-monitor', self.manager._monitor_map)
                mock_monitor_instance.start.assert_not_called()
        
        self.run_async(test_logic())
    
    @override_settings(DEBUG=False, SUPPRESS_MONITORS=False)
    def test_monitors_started_normally(self):
        """Test monitors are started when not suppressed."""
        
        async def test_logic():
            # Create a mock monitor class that returns a configured instance
            mock_monitor_instance = Mock(spec=PeriodicMonitor)
            mock_monitor_instance.id = 'test-monitor'
            mock_monitor_instance.is_running = False
            mock_monitor_instance.start = Mock()
            
            mock_monitor_class = Mock(return_value=mock_monitor_instance)
            
            with patch.object(self.manager, '_discover_periodic_monitors') as mock_discover:
                mock_discover.return_value = [mock_monitor_class]
                
                # Mock asyncio.create_task to verify task creation
                with patch('asyncio.create_task') as mock_create_task:
                    await self.manager.initialize(self._test_loop)
                    
                    # Monitor should be registered and started
                    self.assertIn('test-monitor', self.manager._monitor_map)
                    mock_create_task.assert_called_once()
        
        self.run_async(test_logic())
    
    def test_shutdown_stops_all_monitors(self):
        """Test shutdown() stops all registered monitors."""
        
        async def test_logic():
            # Create mock monitors
            mock_monitor1 = Mock(spec=PeriodicMonitor)
            mock_monitor1.id = 'monitor-1'
            mock_monitor1.stop = Mock()
            
            mock_monitor2 = Mock(spec=PeriodicMonitor)
            mock_monitor2.id = 'monitor-2'
            mock_monitor2.stop = Mock()
            
            # Add monitors to manager
            self.manager._monitor_map = {
                'monitor-1': mock_monitor1,
                'monitor-2': mock_monitor2
            }
            
            # Shutdown
            await self.manager.shutdown()
            
            # Both monitors should be stopped
            mock_monitor1.stop.assert_called_once()
            mock_monitor2.stop.assert_called_once()
        
        self.run_async(test_logic())
    
    def test_already_running_monitor_not_started_again(self):
        """Test that already running monitors are not started again."""
        
        async def test_logic():
            # Create a mock monitor class that returns a configured instance
            mock_monitor_instance = Mock(spec=PeriodicMonitor)
            mock_monitor_instance.id = 'running-monitor'
            mock_monitor_instance.is_running = True  # Already running
            mock_monitor_instance.start = Mock()
            
            mock_monitor_class = Mock(return_value=mock_monitor_instance)
            
            with patch.object(self.manager, '_discover_periodic_monitors') as mock_discover:
                mock_discover.return_value = [mock_monitor_class]
                
                await self.manager.initialize(self._test_loop)
                
                # Monitor should be registered but not started
                self.assertIn('running-monitor', self.manager._monitor_map)
                mock_monitor_instance.start.assert_not_called()
        
        self.run_async(test_logic())
    
    def test_event_loop_stored_on_initialization(self):
        """Test event loop is stored during initialization."""
        
        async def test_logic():
            with patch.object(self.manager, '_discover_periodic_monitors') as mock_discover:
                mock_discover.return_value = []
                
                test_loop = asyncio.get_event_loop()
                await self.manager.initialize(test_loop)
                
                self.assertIs(self.manager._monitor_event_loop, test_loop)
        
        self.run_async(test_logic())

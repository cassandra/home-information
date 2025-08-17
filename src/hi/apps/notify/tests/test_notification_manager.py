import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch
from hi.tests.async_task_utils import AsyncTaskTestCase

from hi.apps.notify.notification_manager import NotificationManager
from hi.apps.notify.settings import NotifySetting
from hi.apps.notify.transient_models import Notification, NotificationItem

logging.disable(logging.CRITICAL)


class AsyncManagerTestCase(AsyncTaskTestCase):
    """Base class for async manager tests with proper infrastructure."""


class TestNotificationManager(AsyncManagerTestCase):

    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        NotificationManager._instances = {}
        self.manager = NotificationManager()

    def test_singleton_pattern_behavior(self):
        """Test NotificationManager follows singleton pattern."""
        manager1 = NotificationManager()
        manager2 = NotificationManager()
        
        # Both instances should be the same object
        self.assertIs(manager1, manager2)
        
        # Verify singleton initialization state is shared
        manager1.ensure_initialized()
        self.assertTrue(manager2._was_initialized)

    def test_initialization_state_management(self):
        """Test initialization state is properly managed."""
        # Initial state should be uninitialized
        self.assertFalse(self.manager._was_initialized)
        
        # First call should initialize
        self.manager.ensure_initialized()
        self.assertTrue(self.manager._was_initialized)
        
        # Subsequent calls should not re-initialize
        with patch.object(self.manager, '__init_singleton__') as mock_init:
            self.manager.ensure_initialized()
            mock_init.assert_not_called()

    def test_notification_queue_initialization(self):
        """Test notification queue is properly initialized."""
        # Verify queue is created during singleton initialization
        self.assertIsNotNone(self.manager._notification_queue)
        
        # Verify it's the expected type
        from hi.apps.notify.notification_queue import NotificationQueue
        self.assertIsInstance(self.manager._notification_queue, NotificationQueue)

    def test_add_notification_item_delegates_to_queue(self):
        """Test add_notification_item properly delegates to internal queue."""
        notification_item = NotificationItem(
            signature='test_signature',
            title='Test Notification',
            source_obj={'data': 'test'}
        )
        
        with patch.object(self.manager._notification_queue, 'add_item') as mock_add:
            self.manager.add_notification_item(notification_item)
            mock_add.assert_called_once_with(notification_item=notification_item)

    def test_periodic_maintenance_retrieves_and_processes_notifications(self):
        """Test periodic maintenance workflow retrieves and processes notifications."""
        async def async_test_logic():
            # Create mock notifications
            notification1 = Notification(
                title='Test Notification 1',
                item_list=[NotificationItem(signature='sig1', title='Test 1')]
            )
            notification2 = Notification(
                title='Test Notification 2',
                item_list=[NotificationItem(signature='sig2', title='Test 2')]
            )
            mock_notifications = [notification1, notification2]
            
            # Mock queue check and notification sending
            with patch.object(self.manager._notification_queue, 'check_for_notifications') as mock_check:
                with patch.object(self.manager, 'send_notifications') as mock_send:
                    mock_check.return_value = mock_notifications
                    mock_send.return_value = True
                    
                    await self.manager.do_periodic_maintenance()
                    
                    # Verify queue was checked
                    mock_check.assert_called_once()
                    
                    # Verify each notification was processed
                    self.assertEqual(mock_send.call_count, 2)
                    mock_send.assert_any_call(notification1)
                    mock_send.assert_any_call(notification2)
        
        self.run_async(async_test_logic())

    def test_periodic_maintenance_handles_exceptions_gracefully(self):
        """Test periodic maintenance gracefully handles exceptions without crashing."""
        async def async_test_logic():
            # Mock queue to raise an exception
            with patch.object(self.manager._notification_queue, 'check_for_notifications') as mock_check:
                mock_check.side_effect = Exception("Test exception")
                
                # Should not raise an exception
                await self.manager.do_periodic_maintenance()
                
                # Verify exception was caught and logged
                mock_check.assert_called_once()
        
        self.run_async(async_test_logic())

    def test_send_notifications_disabled_by_setting(self):
        """Test notifications are blocked when disabled in settings."""
        async def async_test_logic():
            notification = Notification(
                title='Test Notification',
                item_list=[NotificationItem(signature='test', title='Test')]
            )
            
            # Mock settings manager to return disabled
            mock_settings_manager = Mock()
            mock_settings_manager.get_setting_value.return_value = 'False'
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                mock_settings_async.return_value = mock_settings_manager
                
                result = await self.manager.send_notifications(notification)
                
                # Should return False when disabled
                self.assertFalse(result)
                
                # Verify the correct setting was checked
                mock_settings_manager.get_setting_value.assert_called_with(
                    NotifySetting.NOTIFICATIONS_ENABLED
                )
        
        self.run_async(async_test_logic())

    def test_send_notifications_enabled_delegates_to_email_sender(self):
        """Test notifications are sent when enabled in settings."""
        async def async_test_logic():
            notification = Notification(
                title='Test Notification',
                item_list=[NotificationItem(signature='test', title='Test')]
            )
            
            # Mock settings manager to return enabled
            mock_settings_manager = Mock()
            mock_settings_manager.get_setting_value.return_value = 'True'
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                with patch.object(self.manager, 'send_email_notification_if_needed_async') as mock_email_send:
                    mock_settings_async.return_value = mock_settings_manager
                    mock_email_send.return_value = True
                    
                    result = await self.manager.send_notifications(notification)
                    
                    # Should return True when enabled and email sent
                    self.assertTrue(result)
                    
                    # Verify email sending was called
                    mock_email_send.assert_called_once_with(notification=notification)
        
        self.run_async(async_test_logic())

    def test_send_notifications_handles_missing_settings_manager(self):
        """Test send_notifications handles missing settings manager gracefully."""
        async def async_test_logic():
            notification = Notification(
                title='Test Notification',
                item_list=[NotificationItem(signature='test', title='Test')]
            )
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                mock_settings_async.return_value = None
                
                result = await self.manager.send_notifications(notification)
                
                # Should return False when settings manager unavailable
                self.assertFalse(result)
        
        self.run_async(async_test_logic())

    def test_email_notification_with_valid_addresses(self):
        """Test email notification sends when valid addresses configured."""
        async def async_test_logic():
            notification = Notification(
                title='Test Alert',
                item_list=[NotificationItem(signature='alert', title='Alert Item')]
            )
            
            # Mock settings manager with valid email addresses
            mock_settings_manager = Mock()
            mock_settings_manager.get_setting_value.return_value = 'admin@example.com, user@example.com'
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                with patch('hi.apps.notify.notification_manager.EmailSender') as mock_email_sender_class:
                    mock_settings_async.return_value = mock_settings_manager
                    
                    # Mock EmailSender instance
                    mock_sender = Mock()
                    mock_sender.send_async = AsyncMock()
                    mock_email_sender_class.return_value = mock_sender
                    
                    result = await self.manager.send_email_notification_if_needed_async(notification)
                    
                    # Should return True when email sent
                    self.assertTrue(result)
                    
                    # Verify EmailSender was created with correct data
                    mock_email_sender_class.assert_called_once()
                    call_args = mock_email_sender_class.call_args[1]
                    email_data = call_args['data']
                    
                    # Verify email data configuration
                    self.assertEqual(email_data.to_email_address, ['admin@example.com', 'user@example.com'])
                    self.assertEqual(email_data.subject_template_name, 'notify/emails/notification_subject.txt')
                    self.assertEqual(email_data.message_text_template_name, 'notify/emails/notification_message.txt')
                    self.assertEqual(email_data.message_html_template_name, 'notify/emails/notification_message.html')
                    self.assertEqual(email_data.template_context['notification'], notification)
                    self.assertIsNone(email_data.request)
                    
                    # Verify email was sent
                    mock_sender.send_async.assert_called_once()
        
        self.run_async(async_test_logic())

    def test_email_notification_with_no_addresses_configured(self):
        """Test email notification skips sending when no addresses configured."""
        async def async_test_logic():
            notification = Notification(
                title='Test Alert',
                item_list=[NotificationItem(signature='alert', title='Alert Item')]
            )
            
            # Mock settings manager with empty email addresses
            mock_settings_manager = Mock()
            mock_settings_manager.get_setting_value.return_value = ''
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                with patch('hi.apps.notify.notification_manager.EmailSender') as mock_email_sender_class:
                    mock_settings_async.return_value = mock_settings_manager
                    
                    result = await self.manager.send_email_notification_if_needed_async(notification)
                    
                    # Should return False when no addresses configured
                    self.assertFalse(result)
                    
                    # Verify EmailSender was never created
                    mock_email_sender_class.assert_not_called()
        
        self.run_async(async_test_logic())

    def test_email_notification_with_invalid_addresses(self):
        """Test email notification attempts to send when addresses provided (even if invalid format)."""
        async def async_test_logic():
            notification = Notification(
                title='Test Alert',
                item_list=[NotificationItem(signature='alert', title='Alert Item')]
            )
            
            # Mock settings manager with invalid email addresses
            mock_settings_manager = Mock()
            mock_settings_manager.get_setting_value.return_value = 'invalid-email, another-invalid'
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                with patch('hi.apps.notify.notification_manager.EmailSender') as mock_email_sender_class:
                    mock_settings_async.return_value = mock_settings_manager
                    
                    # Mock EmailSender instance
                    mock_sender = Mock()
                    mock_sender.send_async = AsyncMock()
                    mock_email_sender_class.return_value = mock_sender
                    
                    result = await self.manager.send_email_notification_if_needed_async(notification)
                    
                    # Should return True - notification manager doesn't validate email format
                    self.assertTrue(result)
                    
                    # Verify EmailSender was created and called
                    mock_email_sender_class.assert_called_once()
                    mock_sender.send_async.assert_called_once()
        
        self.run_async(async_test_logic())

    def test_email_notification_handles_missing_settings_manager(self):
        """Test email notification handles missing settings manager gracefully."""
        async def async_test_logic():
            notification = Notification(
                title='Test Alert',
                item_list=[NotificationItem(signature='alert', title='Alert Item')]
            )
            
            with patch.object(self.manager, 'settings_manager_async') as mock_settings_async:
                mock_settings_async.return_value = None
                
                result = await self.manager.send_email_notification_if_needed_async(notification)
                
                # Should return False when settings manager unavailable
                self.assertFalse(result)
        
        self.run_async(async_test_logic())

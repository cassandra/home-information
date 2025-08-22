import logging
import threading
import time
from unittest.mock import Mock, patch
from datetime import datetime

from hi.apps.notify.notification_queue import NotificationQueue
from hi.apps.notify.transient_models import Notification, NotificationItem
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestNotificationQueue(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.queue = NotificationQueue()

    def test_notification_queue_initialization(self):
        """Test NotificationQueue initializes with empty state."""
        self.assertEqual(len(self.queue._queues_map), 0)
        self.assertIsNotNone(self.queue._queues_lock)
        # Check that it's a threading lock (can't use isinstance with _thread.lock type)
        self.assertTrue(hasattr(self.queue._queues_lock, 'acquire'))
        self.assertTrue(hasattr(self.queue._queues_lock, 'release'))

    def test_add_item_creates_new_queue_for_signature(self):
        """Test adding item creates new queue for unique signature."""
        notification_item = NotificationItem(
            signature='test_signature',
            title='Test Notification',
            source_obj={'data': 'test'}
        )
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            self.queue.add_item(notification_item)
            
            # Verify queue was created for the signature
            self.assertIn('test_signature', self.queue._queues_map)
            
            # Verify queue contains the item
            queue = self.queue._queues_map['test_signature']
            self.assertEqual(len(queue), 1)

    def test_add_item_reuses_existing_queue_for_same_signature(self):
        """Test adding items with same signature reuses existing queue."""
        item1 = NotificationItem(signature='same_sig', title='Item 1')
        item2 = NotificationItem(signature='same_sig', title='Item 2')
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            self.queue.add_item(item1)
            self.queue.add_item(item2)
            
            # Should have only one queue for the signature
            self.assertEqual(len(self.queue._queues_map), 1)
            self.assertIn('same_sig', self.queue._queues_map)
            
            # Queue should contain both items
            queue = self.queue._queues_map['same_sig']
            self.assertEqual(len(queue), 2)

    def test_add_item_creates_separate_queues_for_different_signatures(self):
        """Test adding items with different signatures creates separate queues."""
        item1 = NotificationItem(signature='sig1', title='Item 1')
        item2 = NotificationItem(signature='sig2', title='Item 2')
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            self.queue.add_item(item1)
            self.queue.add_item(item2)
            
            # Should have two separate queues
            self.assertEqual(len(self.queue._queues_map), 2)
            self.assertIn('sig1', self.queue._queues_map)
            self.assertIn('sig2', self.queue._queues_map)
            
            # Each queue should contain one item
            self.assertEqual(len(self.queue._queues_map['sig1']), 1)
            self.assertEqual(len(self.queue._queues_map['sig2']), 1)

    def test_add_item_handles_exceptions_gracefully(self):
        """Test add_item handles exceptions without breaking queue state."""
        notification_item = NotificationItem(signature='test', title='Test')
        
        # Mock the queue creation to raise an exception
        with patch('hi.apps.notify.notification_queue.ExponentialBackoffRateLimitedQueue') as mock_queue_class:
            mock_queue_class.side_effect = Exception("Test exception")
            
            # Should not raise exception
            self.queue.add_item(notification_item)
            
            # Queue map should remain empty due to exception
            self.assertEqual(len(self.queue._queues_map), 0)

    def test_check_for_notifications_returns_empty_when_no_queues(self):
        """Test check_for_notifications returns empty list when no queues exist."""
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            notifications = self.queue.check_for_notifications()
            
            self.assertEqual(len(notifications), 0)
            self.assertIsInstance(notifications, list)

    def test_check_for_notifications_creates_notification_objects(self):
        """Test check_for_notifications creates proper Notification objects."""
        # Create items
        item1 = NotificationItem(signature='test_sig', title='Test Title 1')
        item2 = NotificationItem(signature='test_sig', title='Test Title 1')  # Same title as item1
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            # Mock the queue to emit items
            mock_queue = Mock()
            mock_queue.__len__ = Mock(return_value=2)  # Mock the len() call
            mock_queue.get_queue_emissions.return_value = [item1, item2]
            self.queue._queues_map['test_sig'] = mock_queue
            
            notifications = self.queue.check_for_notifications()
            
            # Should have one notification
            self.assertEqual(len(notifications), 1)
            notification = notifications[0]
            
            # Verify notification structure
            self.assertIsInstance(notification, Notification)
            self.assertEqual(notification.title, 'Test Title 1')  # Uses first item's title
            self.assertEqual(len(notification.item_list), 2)
            self.assertIn(item1, notification.item_list)
            self.assertIn(item2, notification.item_list)

    def test_check_for_notifications_handles_multiple_signatures(self):
        """Test check_for_notifications handles multiple signature queues."""
        item1 = NotificationItem(signature='sig1', title='Title 1')
        item2 = NotificationItem(signature='sig2', title='Title 2')
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            # Mock queues to emit items
            mock_queue1 = Mock()
            mock_queue1.__len__ = Mock(return_value=1)
            mock_queue1.get_queue_emissions.return_value = [item1]
            mock_queue2 = Mock()
            mock_queue2.__len__ = Mock(return_value=1)
            mock_queue2.get_queue_emissions.return_value = [item2]
            
            self.queue._queues_map['sig1'] = mock_queue1
            self.queue._queues_map['sig2'] = mock_queue2
            
            notifications = self.queue.check_for_notifications()
            
            # Should have two notifications
            self.assertEqual(len(notifications), 2)
            
            # Verify both notifications were created
            titles = [notification.title for notification in notifications]
            self.assertIn('Title 1', titles)
            self.assertIn('Title 2', titles)

    def test_check_for_notifications_skips_empty_emissions(self):
        """Test check_for_notifications skips queues with no emissions."""
        item1 = NotificationItem(signature='sig1', title='Title 1')
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            # Mock queues - one with emissions, one without
            mock_queue1 = Mock()
            mock_queue1.__len__ = Mock(return_value=1)
            mock_queue1.get_queue_emissions.return_value = [item1]
            mock_queue2 = Mock()
            mock_queue2.__len__ = Mock(return_value=0)
            mock_queue2.get_queue_emissions.return_value = []  # No emissions
            
            self.queue._queues_map['sig1'] = mock_queue1
            self.queue._queues_map['sig2'] = mock_queue2
            
            notifications = self.queue.check_for_notifications()
            
            # Should have only one notification (from sig1)
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0].title, 'Title 1')

    def test_check_for_notifications_handles_exceptions_gracefully(self):
        """Test check_for_notifications handles exceptions without breaking."""
        # Add a mock queue that raises an exception
        mock_queue = Mock()
        mock_queue.get_queue_emissions.side_effect = Exception("Test exception")
        self.queue._queues_map['failing_sig'] = mock_queue
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            # Should not raise exception
            notifications = self.queue.check_for_notifications()
            
            # Should return empty list due to exception
            self.assertEqual(len(notifications), 0)

    def test_thread_safety_concurrent_add_operations(self):
        """Test thread safety when multiple threads add items concurrently."""
        num_threads = 5
        items_per_thread = 10
        results = []
        
        def add_items_worker(thread_id):
            """Worker function to add items in a thread."""
            thread_results = []
            for i in range(items_per_thread):
                item = NotificationItem(
                    signature=f'thread_{thread_id}_sig',
                    title=f'Thread {thread_id} Item {i}'
                )
                try:
                    with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
                        mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
                        self.queue.add_item(item)
                    thread_results.append(True)
                except Exception:
                    thread_results.append(False)
            results.extend(thread_results)
        
        # Create and start threads
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=add_items_worker, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        self.assertEqual(len(results), num_threads * items_per_thread)
        self.assertTrue(all(results), "Some thread operations failed")
        
        # Verify queues were created for each thread
        self.assertEqual(len(self.queue._queues_map), num_threads)
        for thread_id in range(num_threads):
            expected_sig = f'thread_{thread_id}_sig'
            self.assertIn(expected_sig, self.queue._queues_map)

    def test_thread_safety_concurrent_check_and_add_operations(self):
        """Test thread safety when mixing check and add operations."""
        add_results = []
        check_results = []
        
        def add_worker():
            """Worker to add items."""
            for i in range(5):
                item = NotificationItem(signature='concurrent_sig', title=f'Item {i}')
                try:
                    with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
                        mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
                        self.queue.add_item(item)
                    add_results.append(True)
                    time.sleep(0.001)  # Small delay to encourage race conditions
                except Exception:
                    add_results.append(False)
        
        def check_worker():
            """Worker to check for notifications."""
            for i in range(5):
                try:
                    with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
                        mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
                        notifications = self.queue.check_for_notifications()
                    check_results.append(len(notifications))
                    time.sleep(0.001)  # Small delay to encourage race conditions
                except Exception:
                    check_results.append(-1)  # Error indicator
        
        # Start both types of workers
        add_thread = threading.Thread(target=add_worker)
        check_thread = threading.Thread(target=check_worker)
        
        add_thread.start()
        check_thread.start()
        
        add_thread.join()
        check_thread.join()
        
        # Verify operations completed without errors
        self.assertEqual(len(add_results), 5)
        self.assertEqual(len(check_results), 5)
        self.assertTrue(all(result for result in add_results), "Some add operations failed")
        self.assertTrue(all(result >= 0 for result in check_results), "Some check operations failed")

    def test_exponential_backoff_queue_integration(self):
        """Test integration with ExponentialBackoffRateLimitedQueue."""
        notification_item = NotificationItem(signature='backoff_test', title='Test')
        
        with patch('hi.apps.notify.notification_queue.datetimeproxy.now') as mock_now:
            test_datetime = datetime(2024, 1, 1, 12, 0, 0)
            mock_now.return_value = test_datetime
            
            # Add item to create queue
            self.queue.add_item(notification_item)
            
            # Verify ExponentialBackoffRateLimitedQueue was created with correct parameters
            queue = self.queue._queues_map['backoff_test']
            from hi.apps.common.queues import ExponentialBackoffRateLimitedQueue
            self.assertIsInstance(queue, ExponentialBackoffRateLimitedQueue)
            
            # Verify the queue label matches signature
            self.assertEqual(queue.label, 'backoff_test')

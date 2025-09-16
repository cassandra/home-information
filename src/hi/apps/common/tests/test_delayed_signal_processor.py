"""
Tests for DelayedSignalProcessor functionality.
Focuses on high-value testing: threading, transaction coordination, and state management.
"""

import threading
import time
from unittest.mock import Mock, patch
from django.test import TransactionTestCase
from django.db import transaction

from hi.apps.common.delayed_signal_processor import DelayedSignalProcessor


class TestDelayedSignalProcessor(TransactionTestCase):
    """Test DelayedSignalProcessor threading and transaction coordination."""

    def setUp(self):
        self.callback_mock = Mock()
        self.processor = DelayedSignalProcessor(
            name="test_processor",
            callback_func=self.callback_mock,
            delay_seconds=0.01  # Short delay for testing
        )

    def test_single_execution_within_transaction(self):
        """HIGH-VALUE: Test deduplication within transactions."""
        with transaction.atomic():
            # Multiple calls within same transaction
            self.processor.schedule_processing()
            self.processor.schedule_processing()
            self.processor.schedule_processing()

        # Wait for delayed execution
        time.sleep(0.05)

        # Should only execute once despite multiple calls
        self.assertEqual(self.callback_mock.call_count, 1)

    def test_multiple_sequential_executions(self):
        """HIGH-VALUE: Test that subsequent calls work (catches the threading bug)."""
        # First execution
        with transaction.atomic():
            self.processor.schedule_processing()
        time.sleep(0.05)  # Wait for execution

        # Second execution - this would fail with the original bug
        with transaction.atomic():
            self.processor.schedule_processing()
        time.sleep(0.05)  # Wait for execution

        # Third execution to be thorough
        with transaction.atomic():
            self.processor.schedule_processing()
        time.sleep(0.05)  # Wait for execution

        # Should have been called three times
        self.assertEqual(self.callback_mock.call_count, 3)

    def test_timer_cancellation_behavior(self):
        """HIGH-VALUE: Test rapid call debouncing."""
        # Start first call
        with transaction.atomic():
            self.processor.schedule_processing()

        # Before first execution, make another call (should cancel first)
        time.sleep(0.005)  # Half the delay
        with transaction.atomic():
            self.processor.schedule_processing()

        # Wait for final execution
        time.sleep(0.05)

        # Should only execute once (second call cancels first)
        self.assertEqual(self.callback_mock.call_count, 1)

    def test_processing_registered_flag_reset_behavior(self):
        """HIGH-VALUE: Test internal state management that caused the bug."""
        # First execution
        with transaction.atomic():
            self.processor.schedule_processing()
            # Flag should be set during transaction
            self.assertTrue(self.processor._thread_local.processing_registered)

        # Wait for execution to complete
        time.sleep(0.05)

        # Flag should be reset after transaction commits and processing starts
        # Note: We can't directly check the flag state after background execution
        # because the background thread has its own thread-local storage.
        # Instead, we verify that subsequent calls work.

        # Second execution should work (proves flag was reset)
        with transaction.atomic():
            self.processor.schedule_processing()
        time.sleep(0.05)

        self.assertEqual(self.callback_mock.call_count, 2)

    def test_thread_safety_across_concurrent_transactions(self):
        """HIGH-VALUE: Test thread-local storage isolation."""
        results = []

        def thread_function(thread_id):
            with transaction.atomic():
                self.processor.schedule_processing()
            # Store thread completion
            results.append(thread_id)

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_function, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Wait for delayed executions
        time.sleep(0.1)

        # All threads should have completed
        self.assertEqual(len(results), 3)
        # Callback should execute at least once (exact count depends on timing)
        self.assertGreaterEqual(self.callback_mock.call_count, 1)

    def test_exception_handling_in_callback(self):
        """HIGH-VALUE: Test error handling doesn't break future calls."""
        # Create processor with callback that raises exception
        error_callback = Mock(side_effect=Exception("Test error"))
        error_processor = DelayedSignalProcessor(
            name="error_processor",
            callback_func=error_callback,
            delay_seconds=0.01
        )

        # First call should handle exception gracefully
        with transaction.atomic():
            error_processor.schedule_processing()
        time.sleep(0.05)

        # Second call should still work despite previous exception
        with transaction.atomic():
            error_processor.schedule_processing()
        time.sleep(0.05)

        # Both calls should have been attempted
        self.assertEqual(error_callback.call_count, 2)

    def test_callback_execution_context(self):
        """Test that callback executes in background thread with proper context."""
        execution_details = {}

        def context_callback():
            execution_details['thread_name'] = threading.current_thread().name
            execution_details['called'] = True

        processor = DelayedSignalProcessor(
            name="context_processor",
            callback_func=context_callback,
            delay_seconds=0.01
        )

        main_thread_name = threading.current_thread().name

        with transaction.atomic():
            processor.schedule_processing()

        time.sleep(0.05)

        # Verify callback was executed
        self.assertTrue(execution_details.get('called', False))
        # Verify it ran in a different (background) thread
        self.assertNotEqual(execution_details['thread_name'], main_thread_name)

    def test_daemon_thread_behavior(self):
        """Test that timer threads are properly configured as daemon threads."""
        with transaction.atomic():
            self.processor.schedule_processing()

        # Give timer a moment to start
        time.sleep(0.005)

        # Timer should exist and be daemon
        self.assertIsNotNone(self.processor._timer)
        self.assertTrue(self.processor._timer.daemon)

    def test_signal_handler_creation(self):
        """Test signal handler factory method."""
        handler = self.processor.create_signal_handler()

        # Handler should be callable
        self.assertTrue(callable(handler))

        # Handler should accept Django signal parameters
        with transaction.atomic():
            handler(sender=Mock(), instance=Mock(), created=True)

        time.sleep(0.05)

        # Should trigger callback
        self.assertEqual(self.callback_mock.call_count, 1)

    def test_multiple_processors_independence(self):
        """Test that multiple processor instances don't interfere."""
        callback2 = Mock()
        processor2 = DelayedSignalProcessor(
            name="processor2",
            callback_func=callback2,
            delay_seconds=0.01
        )

        # Schedule on both processors
        with transaction.atomic():
            self.processor.schedule_processing()
            processor2.schedule_processing()

        time.sleep(0.05)

        # Both should execute independently
        self.assertEqual(self.callback_mock.call_count, 1)
        self.assertEqual(callback2.call_count, 1)

    def test_rapid_successive_calls_with_different_transactions(self):
        """Test rapid calls across different transactions."""
        # Make multiple calls with longer delays to avoid debouncing
        for _ in range(3):
            with transaction.atomic():
                self.processor.schedule_processing()
            time.sleep(0.03)  # Longer delay to allow each execution to complete

        # Wait for final execution to complete
        time.sleep(0.05)

        # Should execute multiple times (one per transaction)
        self.assertEqual(self.callback_mock.call_count, 3)

    def test_no_callback_execution_without_transaction_commit(self):
        """Test that callback doesn't execute if transaction doesn't commit."""
        try:
            with transaction.atomic():
                self.processor.schedule_processing()
                # Force transaction rollback
                raise Exception("Force rollback")
        except Exception:
            pass  # Expected exception

        time.sleep(0.05)

        # Callback should not have been executed due to rollback
        self.assertEqual(self.callback_mock.call_count, 0)

    @patch('hi.apps.common.delayed_signal_processor.logger')
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate debug logging occurs."""
        with transaction.atomic():
            self.processor.schedule_processing()

        time.sleep(0.05)

        # Verify debug logging was called
        mock_logger.debug.assert_called()

        # Check that processor name appears in log messages
        log_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
        processor_name_in_logs = any('test_processor' in msg for msg in log_calls)
        self.assertTrue(processor_name_in_logs)
        

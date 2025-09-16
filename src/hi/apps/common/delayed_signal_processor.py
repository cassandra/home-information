import logging
from threading import local, Timer
from typing import Callable

from django.db import transaction

logger = logging.getLogger(__name__)


class DelayedSignalProcessor:
    """
    General mechanism for delayed processing of Django model signals.
    
    This class prevents duplicate processing when multiple related models change 
    in one transaction by:
    1. Using thread-local storage to deduplicate signals within a transaction
    2. Delaying execution until after the transaction commits
    3. Running the callback in a background thread to avoid blocking
    4. Canceling pending executions if new signals arrive
    
    Usage:
        processor = DelayedSignalProcessor(
            name="my_processor",
            callback_func=my_reload_function,
            delay_seconds=0.1
        )
        
        @receiver(post_save, sender=MyModel)
        def my_model_changed(sender, instance, **kwargs):
            processor.schedule_processing()
    """
    
    def __init__(self, name: str, callback_func: Callable[[], None], delay_seconds: float = 0.1):
        self.name = name
        self.callback_func = callback_func
        self.delay_seconds = delay_seconds
        self._timer = None
        self._thread_local = local()
        return
    
    def schedule_processing(self):
        """
        This method can be called multiple times within a transaction,
        but the callback will only be scheduled once.
        """

        if not hasattr(self._thread_local, "processing_registered"):
            self._thread_local.processing_registered = False
        
        logger.debug(f'{self.name} model change detected.')
        
        # Only schedule once per transaction
        if not self._thread_local.processing_registered:
            logger.debug(f'Queuing {self.name} processing on model change.')
            self._thread_local.processing_registered = True
            transaction.on_commit(self._queue_delayed_processing)
    
    def _queue_delayed_processing(self):
        # Cancel any existing timer to avoid duplicate processing
        if self._timer and self._timer.is_alive():
            self._timer.cancel()

        # Reset the flag immediately since we're about to schedule processing
        # This allows new signals to schedule additional processing if needed
        self._thread_local.processing_registered = False

        # Schedule the processing to run in a background thread after delay
        # The delay ensures the current transaction can complete first
        self._timer = Timer(self.delay_seconds, self._execute_processing_background)
        self._timer.daemon = True  # Don't prevent process shutdown
        self._timer.start()

        logger.debug(f'Scheduled {self.name} processing in background thread.')
    
    def _execute_processing_background(self):
        try:
            logger.debug(f'Executing {self.name} processing in background thread.')
            self.callback_func()
            logger.debug(f'Background {self.name} processing completed successfully.')
        except Exception as e:
            logger.error(f'Error during background {self.name} processing: {e}')
        finally:
            # Only clear the timer reference - the processing_registered flag
            # was already reset in _queue_delayed_processing in the main thread
            self._timer = None
    
    def create_signal_handler(self):
        """
        Create a signal handler function that can be used with @receiver.
        
        Returns:
            Function that can be used as a Django signal handler
            
        Example:
            processor = DelayedSignalProcessor("my_processor", my_callback)
            signal_handler = processor.create_signal_handler()
            
            @receiver(post_save, sender=MyModel)
            def my_model_changed(sender, instance, **kwargs):
                signal_handler(sender, instance, **kwargs)
        """
        def signal_handler(sender, instance, **kwargs):
            self.schedule_processing()
        return signal_handler
    

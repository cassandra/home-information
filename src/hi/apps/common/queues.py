import collections
from datetime import datetime, timedelta
from typing import Optional, List

import hi.apps.common.datetimeproxy as datetimeproxy


class RateLimitError(Exception):
    """Raised when rate limits are exceeded and no items can be dequeued."""
    pass


class EmptyQueueError(Exception):
    """Raised when there are no items left in the queue."""
    pass


class RateLimitedQueue:
    """
    A queue that emits items one at a time in a rate-limited manner.

    Note: This class is not thread-safe.
    """
    def __init__( self,
                  label               : str,
                  emit_interval_secs  : int   = 30,
                  max_queue_size      : int   = 30,
                  unique_items_only   : bool  = True ):
        self._label = label
        self._emit_interval_secs = emit_interval_secs
        self._unique_items_only = unique_items_only
        self._queue = collections.deque( maxlen = max_queue_size )
        self._next_emit_datetime = datetimeproxy.min()
        return

    @property
    def label(self) -> str:
        return self._label

    def __len__(self) -> int:
        return len(self._queue)

    def get_next_item(self, cur_datetime: Optional[datetime] = None):
        """
        Returns the next item in the queue if rate limits allow. Raises exceptions otherwise.
        """
        if not self._queue:
            raise EmptyQueueError("No items in queue.")

        cur_datetime = cur_datetime or datetimeproxy.now()

        if cur_datetime < self._next_emit_datetime:
            raise RateLimitError("Rate limit reached.")

        self._next_emit_datetime = cur_datetime + timedelta( seconds = self._emit_interval_secs )
        return self._queue.popleft()

    def add_to_queue(self, item) -> bool:
        """
        Adds an item to the queue if unique_items_only is False or if the item is not already in the queue.
        """
        if self._unique_items_only and item in self._queue:
            return False
        self._queue.append(item)
        return True

    def clear_queue(self):
        self._queue.clear()
        return
    

class ExponentialBackoffRateLimitedQueue:
    """
    A queue that emits items in a rate-limited manner with exponential backoff.

    Note: This class is not thread-safe.
    """
    INITIAL_EMIT_INTERVAL_SECS = 60
    EMIT_INTERVAL_BACKOFF_FACTOR = 2
    MAX_EMIT_INTERVAL_SECS = 3600

    def __init__( self,
                  label                 : str,
                  first_emit_datetime  : datetime ):
        self._label = label
        self._queue = list()
        self._emit_delay_secs = 0
        self._next_emit_datetime = first_emit_datetime

    @property
    def label(self) -> str:
        return self._label

    def __len__(self) -> int:
        return len(self._queue)

    def get_queue_emissions( self, cur_datetime : datetime ) -> List:
        """
        Returns a list of items in the queue if rate limits allow. Emits all items that
        have been queued since the last emission.
        """
        if not self._queue or ( cur_datetime < self._next_emit_datetime ):
            return list()

        items = self._queue[:]
        self._queue.clear()

        time_since_last_emit = cur_datetime - self._next_emit_datetime
        if time_since_last_emit.total_seconds() > self.MAX_EMIT_INTERVAL_SECS:
            self._emit_delay_secs = 0

        self._emit_delay_secs = max(
            self._emit_delay_secs * self.EMIT_INTERVAL_BACKOFF_FACTOR
            if self._emit_delay_secs
            else self.INITIAL_EMIT_INTERVAL_SECS,
            
            self.MAX_EMIT_INTERVAL_SECS
        )
        self._next_emit_datetime = cur_datetime + timedelta( seconds = self._emit_delay_secs )

        return items

    def add_to_queue( self, item ):
        self._queue.append(item)
        return

    def clear_queue(self):
        self._queue.clear()
        return

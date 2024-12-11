import logging
import threading
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.queues import ExponentialBackoffRateLimitedQueue

from .transient_models import Notification, NotificationItem

logger = logging.getLogger(__name__)


class NotificationQueue:

    def __init__(self):
        self._queues_map = dict()
        self._queues_lock = threading.Lock()
        return
    
    def add_item( self, notification_item : NotificationItem ):
        logger.debug( f'Adding notification to queue: {notification_item}' )
        try:
            self._queues_lock.acquire()

            if notification_item.signature not in self._queues_map:
                now_datetime = datetimeproxy.now()
                self._queues_map[notification_item.signature] = ExponentialBackoffRateLimitedQueue(
                    label = notification_item.signature,
                    first_emit_datetime = now_datetime,
                )
            queue = self._queues_map[notification_item.signature]
            queue.add_to_queue( notification_item )

        except Exception as e:
            logger.exception( 'Problem adding notification to notification queue.', e )
        finally:
            self._queues_lock.release()
        return
    
    def check_for_notifications( self ) -> List[ Notification ]:
        notifications_map = dict()
        try:
            self._queues_lock.acquire()

            now = datetimeproxy.now()
            for signature, queue in self._queues_map.items():
                logger.debug( f'Notify queue "{signature}" contains {len(queue)} items.' )
                notification_item_list = queue.get_queue_emissions( cur_datetime = now )
                if len(notification_item_list) < 1:
                    continue
                notification = Notification(
                    title = notification_item_list[0].title,
                    item_list = notification_item_list,
                )
                notifications_map[signature] = notification
                logger.debug( f'Notify queue "{signature}" emitted {len(notification_item_list)} items.' )
                continue

        except Exception as e:
            logger.exception( 'Problem checking notification queues.', e )
        finally:
            self._queues_lock.release()

        return list( notifications_map.items() )
            

import random

from hi.apps.notify.transient_models import Notification, NotificationItem


class NotifySyntheticData:

    def create_random_notification( self ):

        item_list = list()
        for item_idx in range( random.randint( 1, 5 )):
            item = NotificationItem(
                signature = f'signature-{item_idx}',
                title = f'This is notification item {item_idx}',
            )
            item_list.append( item )
            continue

        return Notification(
            title = 'Test Notification',
            item_list = item_list,
        )

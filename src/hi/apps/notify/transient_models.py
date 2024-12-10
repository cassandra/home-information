from dataclasses import dataclass
from typing import List


@dataclass
class NotificationItem:
    signature   : str


@dataclass
class Notification:
    item_list   : List[ NotificationItem ]
    

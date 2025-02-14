from dataclasses import dataclass
from typing import List
    
    
@dataclass
class NotificationItem:
    signature     : str
    title         : str
    source_obj    : object  = None
    

@dataclass
class Notification:
    title         : str
    item_list     : List[ NotificationItem ]

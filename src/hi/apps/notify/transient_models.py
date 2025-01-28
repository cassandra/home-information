from dataclasses import dataclass, field
from typing import Dict, List, Union

from django.http.request import HttpRequest
    
    
@dataclass
class NotificationItem:
    signature     : str
    title         : str
    source_obj    : object  = None
    

@dataclass
class Notification:
    title         : str
    item_list     : List[ NotificationItem ]

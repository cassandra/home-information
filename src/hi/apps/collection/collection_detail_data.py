from dataclasses import dataclass

from hi.apps.location.forms import LocationItemPositionForm

from .models import Collection


@dataclass
class CollectionDetailData:

    collection                   : Collection
    location_item_position_form  : LocationItemPositionForm
    

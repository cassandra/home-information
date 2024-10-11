from dataclasses import dataclass

from hi.apps.location.forms import LocationItemPositionForm

from .models import Entity


@dataclass
class EntityDetailData:

    entity                       : Entity
    location_item_position_form  : LocationItemPositionForm
    

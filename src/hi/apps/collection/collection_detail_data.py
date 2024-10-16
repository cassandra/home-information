from dataclasses import dataclass

from hi.apps.collection.edit.forms import CollectionPositionForm

from .models import Collection


@dataclass
class CollectionDetailData:

    collection                : Collection
    collection_position_form  : CollectionPositionForm
    

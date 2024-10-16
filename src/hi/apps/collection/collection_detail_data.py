from dataclasses import dataclass

from hi.apps.collection.edit.forms import CollectionForm, CollectionPositionForm

from .models import Collection


@dataclass
class CollectionDetailData:

    collection                : Collection
    collection_form           : CollectionForm
    collection_position_form  : CollectionPositionForm
    

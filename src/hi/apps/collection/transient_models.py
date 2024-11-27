from dataclasses import dataclass, field
from typing import List

from hi.apps.collection.edit.forms import CollectionForm, CollectionPositionForm
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import EntityInfoData

from .models import Collection


@dataclass
class CollectionData:

    collection             : Collection
    entity_info_data_list  : List[ EntityInfoData ]

    
@dataclass
class CollectionViewItem:

    collection      : Collection
    exists_in_view  : bool


@dataclass
class CollectionViewGroup:

    item_list      : List[CollectionViewItem]  = field( default_factory = list )


@dataclass
class EntityCollectionItem:

    entity                : Entity
    exists_in_collection  : bool


@dataclass
class EntityCollectionGroup:

    collection   : Collection
    entity_type  : EntityType
    item_list    : List[EntityCollectionItem]  = field( default_factory = list )
    

@dataclass
class CollectionEditData:
    """ All the data needed to render the Collection edit pane (subset of all collection details). """

    collection                : Collection
    collection_form           : CollectionForm  = None

    def __post_init__(self):

        if not self.collection_form:
            self.collection_form = CollectionForm(
                instance = self.collection,
            )
        return
    
    def to_template_context(self):
        return {
            'collection': self.collection,
            'collection_form': self.collection_form,
        }
    

@dataclass
class CollectionDetailsData:
    """ All the data needed to render the Collection details pane. """

    collection_edit_data      : CollectionEditData
    collection_position_form  : CollectionPositionForm  = None
    
    def to_template_context(self):
        context = {
            'collection_position_form': self.collection_position_form,
        }
        context.update( self.collection_edit_data.to_template_context() )
        return context

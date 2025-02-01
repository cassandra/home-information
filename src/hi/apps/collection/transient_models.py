from dataclasses import dataclass, field
from typing import List

from hi.apps.collection.edit.forms import CollectionEditForm, CollectionPositionForm
from hi.apps.entity.enums import EntityGroupType
from hi.apps.entity.models import Entity
from hi.apps.monitor.transient_models import EntityStatusData

from .models import Collection


@dataclass
class CollectionData:

    collection               : Collection
    entity_status_data_list  : List[ EntityStatusData ]
    
    def to_template_context(self):
        return {
            'collection': self.collection,
            'entity_status_data_list': self.entity_status_data_list,
        }

    
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

    collection         : Collection
    entity_group_type  : EntityGroupType
    item_list          : List[EntityCollectionItem]  = field( default_factory = list )
    

@dataclass
class CollectionEditData:
    """ All the data needed to render the Collection edit pane (subset of all collection details). """

    collection            : Collection
    collection_edit_form  : CollectionEditForm  = None

    def __post_init__(self):

        if not self.collection_edit_form:
            self.collection_edit_form = CollectionEditForm(
                instance = self.collection,
            )
        return
    
    def to_template_context(self):
        return {
            'collection': self.collection,
            'collection_edit_form': self.collection_edit_form,
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

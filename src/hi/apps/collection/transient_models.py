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
            'collection_grid_css_class': self.grid_css_class,
            'entity_count': len(self.entity_status_data_list),
        }

    @property
    def grid_css_class(self):
        entity_count = len(self.entity_status_data_list)
        if entity_count >= 3:
            return 'grid-3-plus-items'
        if entity_count == 2:
            return 'grid-2-items'
        return 'grid-1-item'
        
    
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
    is_unused             : bool = False


@dataclass
class EntityCollectionGroup:

    collection         : Collection
    entity_group_type  : EntityGroupType
    item_list          : List[EntityCollectionItem]  = field( default_factory = list )
    

@dataclass
class CollectionEditModeData:
    """ All the data needed to render the Collection details pane. """

    collection                : Collection
    collection_edit_form      : CollectionEditForm  = None
    collection_position_form  : CollectionPositionForm  = None

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
            'collection_position_form': self.collection_position_form,
        }

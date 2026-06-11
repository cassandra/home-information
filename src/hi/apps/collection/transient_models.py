from dataclasses import dataclass, field
from typing import List

from hi.apps.collection.edit.forms import CollectionEditForm, CollectionPositionForm
from hi.apps.entity.enums import EntityGroupType
from hi.apps.entity.models import Entity
from hi.apps.entity.state_panel_dispatch import EntityStatePanelData

from .models import Collection


@dataclass
class CollectionData:

    collection             : Collection
    state_panel_data_list : List[ EntityStatePanelData ]

    def to_template_context(self):
        return {
            'collection': self.collection,
            'state_panel_data_list': self.state_panel_data_list,
            'entity_count': len(self.state_panel_data_list),
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
    is_unused             : bool = False


@dataclass
class EntityCollectionGroup:

    collection         : Collection
    entity_group_type  : EntityGroupType
    item_list          : List[EntityCollectionItem]  = field( default_factory = list )


@dataclass
class CollectionEntityPickerData:
    """The two sections of the Collection item picker, built together from
    a single entity scan: the type-grouped non-delegate entities and the
    flat delegate ("Paired Items") list."""

    entity_collection_group_list  : List[EntityCollectionGroup]  = field( default_factory = list )
    delegate_view_item_list       : List[EntityCollectionItem]   = field( default_factory = list )


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

from dataclasses import dataclass, field
from typing import List

from hi.apps.entity.edit.forms import (
    EntityAttributeFormSet,
    EntityForm,
    EntityPositionForm,
    EntityAttributeUploadForm,
)
from hi.apps.location.models import LocationView

from .enums import EntityType
from .models import Entity, EntityState


@dataclass
class EntityViewItem:

    entity          : Entity
    exists_in_view  : bool


@dataclass
class EntityViewGroup:
    """ All entities of a given type and flagged as in the view or not. """
    
    location_view  : LocationView
    entity_type    : EntityType
    item_list      : List[EntityViewItem]  = field( default_factory = list )


@dataclass
class EntityEditData:
    """ All the data needed to render the Entity edit pane (subset of all entity details). """
    
    entity                        : Entity
    entity_form                   : EntityForm                 = None
    entity_attribute_formset      : EntityAttributeFormSet     = None
    entity_attribute_upload_form  : EntityAttributeUploadForm  = None

    def __post_init__(self):

        if not self.entity_form:
            self.entity_form = EntityForm(
                instance = self.entity,
            )
        if not self.entity_attribute_formset:
            self.entity_attribute_formset = EntityAttributeFormSet(
                instance = self.entity,
                prefix = f'entity-{self.entity.id}',
                form_kwargs = {
                    'show_as_editable': True,
                },
            )
        if not self.entity_attribute_upload_form:
            self.entity_attribute_upload_form = EntityAttributeUploadForm()
            
        return
    
    def to_template_context(self):
        return {
            'entity': self.entity,
            'entity_form': self.entity_form,
            'entity_attribute_formset': self.entity_attribute_formset,
            'entity_attribute_upload_form': self.entity_attribute_upload_form,
        }

    
@dataclass
class EntityInfoData:
    """ All the data needed to render the Entity info modal. """

    entity_edit_data       : EntityEditData
    entity_state_list      : List[ EntityState ]
    principal_state_list   : List[ EntityState ]
    principal_entity_list  : List[ Entity ]
    
    def to_template_context(self):
        context = {
            'entity': self.entity_edit_data.entity,
            'entity_state_list': self.entity_state_list,
            'principal_state_list': self.principal_state_list,
            'principal_entity_list': self.principal_entity_list,
        }
        context.update( self.entity_edit_data.to_template_context() )
        return context

    
@dataclass
class EntityDetailsData:
    """ All the data needed to render the Entity details pane. """

    entity_edit_data      : EntityEditData
    entity_position_form  : EntityPositionForm  = None

    def to_template_context(self):
        context = {
            'entity_position_form': self.entity_position_form,
        }
        context.update( self.entity_edit_data.to_template_context() )
        return context

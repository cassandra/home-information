from dataclasses import dataclass, field
from typing import Dict, List

from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.entity.edit.forms import EntityPositionForm
from hi.apps.sense.models import Sensor, SensorHistory

from .enums import EntityGroupType, EntityPairingType
from .forms import (
    EntityAttributeFormSet,
    EntityForm,
    EntityAttributeUploadForm,
)
from .models import Entity


@dataclass
class EntityViewItem:

    entity          : Entity
    exists_in_view  : bool

    
@dataclass
class EntityViewGroup:
    """All entities of a given type and flagged as in the view or not."""
    
    entity_group_type  : EntityGroupType
    item_list          : List[EntityViewItem]  = field( default_factory = list )

    
@dataclass
class EntityPairing:
    """
    An "Entity Pair: abstracts the concepts of principal and delegate
    entities to a simpler, non-directional view for end users.  We only
    allow an entity to participate as a principal or a delegate, not
    both. Further, We only allow a primcipal entity to delegate if it has
    EntityStates and we do not allow delegates to have their own
    state. Thus, by just pairing two entities, we can deduce which
    direction the delagation relatiojnship goes.
    """
    entity         : Entity
    paired_entity  : Entity
    pairing_type   : EntityPairingType
    

@dataclass
class EntityEditData:
    """ Data needed for editing the entity object and its attributes."""
    
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
            'history_url_name': 'entity_attribute_history',
            'restore_url_name': 'entity_attribute_restore',
        }

    
@dataclass
class EntityDetailsData:
    """
    All the data needed about an entity to display in side bar during edit
    mode.
    """

    entity_edit_data      : EntityEditData
    entity_position_form  : EntityPositionForm     = None
    entity_pairing_list   : List[ EntityPairing ]  = None

    def to_template_context(self):
        context = {
            'entity_position_form': self.entity_position_form,
            'entity_pairing_list': self.entity_pairing_list,
        }
        context.update( self.entity_edit_data.to_template_context() )
        return context

    
@dataclass
class EntityStateHistoryData:

    entity                       : Entity
    sensor_history_list_map      : Dict[ Sensor, List[ SensorHistory ] ]
    controller_history_list_map  : Dict[ Controller, List[ ControllerHistory ] ]
    
    def to_template_context(self):
        context = {
            'entity': self.entity,
            'sensor_history_list_map': self.sensor_history_list_map,
            'controller_history_list_map': self.controller_history_list_map,
        }
        return context


from dataclasses import dataclass

from hi.apps.entity.edit.forms import EntityAttributeFormset, EntityForm, EntityPositionForm

from .models import Entity


@dataclass
class EntityDetailData:

    entity                    : Entity
    entity_form               : EntityForm
    entity_attribute_formset  : EntityAttributeFormset
    entity_position_form      : EntityPositionForm
    

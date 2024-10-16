from dataclasses import dataclass

from hi.apps.entity.edit.forms import EntityPositionForm

from .models import Entity


@dataclass
class EntityDetailData:

    entity                : Entity
    entity_position_form  : EntityPositionForm
    

from typing import List

from django.db import transaction

from hi.apps.attribute.enums import AttributeType
from hi.apps.common.singleton import Singleton

from .enums import SubsystemType, SubsystemAttributeType
from .models import Subsystem, SubsystemAttribute


class SystemSettings( Singleton ):

    def __init_singleton__( self ):
        return

    def get_subsystems(self) -> List[ Subsystem ]:
            
        existing_subsystem_map = { x.subsystem_type: x for x in Subsystem.objects.all() }

        subsystem_list = list()
        with transaction.atomic():
            for subsystem_type in SubsystemType:
                if subsystem_type in existing_subsystem_map:
                    subsystem = existing_subsystem_map[subsystem_type]
                else:
                    subsystem = self._create_subsystem( subsystem_type )
                subsystem_list.append( subsystem )
                continue
        
        return subsystem_list
        
    def _create_subsystem( self, subsystem_type : SubsystemType ):
        subsystem = Subsystem.objects.create(
            name = subsystem_type.label,
            subsystem_type_str = str(subsystem_type),
        )
        for subsystem_attribute_type in SubsystemAttributeType:
            if subsystem_type != subsystem_attribute_type.subsystem_type:
                continue
            SubsystemAttribute.objects.create(
                subsystem = subsystem,
                name = subsystem_attribute_type.label,
                value = subsystem_attribute_type.initial_value,
                value_type_str = str(subsystem_attribute_type.value_type),
                attribute_type_str = AttributeType.PREDEFINED,
                is_editable = subsystem_attribute_type.is_editable,
                is_required = subsystem_attribute_type.is_required,
            )
            continue
        return subsystem
    

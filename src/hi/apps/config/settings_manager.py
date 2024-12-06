from typing import List

from django.db import transaction

from hi.apps.attribute.enums import AttributeType
from hi.apps.common.singleton import Singleton

from .enums import SubsystemType, SubsystemAttributeType
from .models import Subsystem, SubsystemAttribute


class SettingsManager( Singleton ):

    def __init_singleton__( self ):
        self._subsystem_list = list()
        self.reload()
        return

    def reload(self):
        self._subsystem_list = self._load_subsystem_list()
        return
    
    def get_subsystems(self) -> List[ Subsystem ]:
        return self._subsystem_list
    
    def _load_subsystem_list(self):
        existing_subsystem_map = {
            x.subsystem_type: x
            for x in Subsystem.objects.prefetch_related('attributes').all()
        }

        subsystem_list = list()
        with transaction.atomic():
            for subsystem_type in SubsystemType:
                if subsystem_type in existing_subsystem_map:
                    subsystem = self._ensure_all_attributes(
                        subsystem = existing_subsystem_map[subsystem_type],
                    )
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
            self._create_attribute(
                subsystem = subsystem,
                subsystem_attribute_type = subsystem_attribute_type,
            )
            continue
        return subsystem
    
    def _ensure_all_attributes( self, subsystem : Subsystem ):

        existing_attr_types = { x.subsystem_attribute_type for x in subsystem.attributes.all() }
        
        for subsystem_attribute_type in SubsystemAttributeType:
            if subsystem.subsystem_type != subsystem_attribute_type.subsystem_type:
                continue
            if subsystem_attribute_type not in existing_attr_types:
                self._create_attribute(
                    subsystem = subsystem,
                    subsystem_attribute_type = subsystem_attribute_type,
                )
            continue
        return subsystem

    def _create_attribute( self,
                           subsystem                 : Subsystem,
                           subsystem_attribute_type  : SubsystemAttributeType ) -> SubsystemAttribute:
        return SubsystemAttribute.objects.create(
            subsystem = subsystem,
            subsystem_attribute_type_str = str(subsystem_attribute_type),
            name = subsystem_attribute_type.label,
            value = subsystem_attribute_type.initial_value,
            value_type_str = str(subsystem_attribute_type.value_type),
            value_range_str = subsystem_attribute_type.value_range_str,
            attribute_type_str = AttributeType.PREDEFINED,
            is_editable = subsystem_attribute_type.is_editable,
            is_required = subsystem_attribute_type.is_required,
        )
        

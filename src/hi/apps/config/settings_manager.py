import logging
from threading import local
from typing import List

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from hi.apps.attribute.enums import AttributeType
from hi.apps.common.singleton import Singleton

from .enums import SubsystemType, SubsystemAttributeType
from .models import Subsystem, SubsystemAttribute

logger = logging.getLogger(__name__)


class SettingsManager( Singleton ):

    def __init_singleton__( self ):
        self._subsystem_list = list()
        self._attribute_value_map = dict()
        self.reload()
        return

    def reload(self):
        self._subsystem_list = self._load_subsystem_list()

        self._attribute_value_map = dict()
        for subsystem in self._subsystem_list:
            for subsystem_attribute in subsystem.attributes.all():
                attr_type = subsystem_attribute.subsystem_attribute_type
                self._attribute_value_map[attr_type] = subsystem_attribute.value
                continue
            continue
        return
    
    def get_subsystems(self) -> List[ Subsystem ]:
        return self._subsystem_list

    def get_setting_value( self, subsystem_attribute_type : SubsystemAttributeType ):
        return self._attribute_value_map.get( subsystem_attribute_type )
    
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

    
_thread_local = local()


def do_settings_manager_reload():
    logger.debug( 'Reloading SettingsManager from model changes.')
    SettingsManager().reload()
    _thread_local.reload_registered = False
    return


@receiver( post_save, sender = Subsystem )
@receiver( post_save, sender = SubsystemAttribute )
@receiver( post_delete, sender = Subsystem )
@receiver( post_delete, sender = SubsystemAttribute )
def settings_manager_model_changed( sender, instance, **kwargs ):
    """
    Queue the SettingsManager.reload() call to execute after the transaction
    is committed.  This prsettingss reloading multiple times if multiple
    models saved as part of a transaction (which is the normal case for
    SettingsDefinition and its related models.)
    """
    if not hasattr(_thread_local, "reload_registered"):
        _thread_local.reload_registered = False

    logger.debug( 'SettingsManager model change detected.')
        
    if not _thread_local.reload_registered:
        logger.debug( 'Queuing SettingsManager reload on model change.')
        _thread_local.reload_registered = True
        transaction.on_commit( do_settings_manager_reload )
    
    return
        

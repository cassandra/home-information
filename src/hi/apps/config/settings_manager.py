from datetime import datetime
import logging
from threading import local, Lock
from typing import List

from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from hi.apps.attribute.enums import AttributeType
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.module_utils import import_module_safe
from hi.apps.common.singleton import Singleton

from .app_settings import AppSettings
from .models import Subsystem, SubsystemAttribute
from .setting_enums import SettingDefinition, SettingEnum

logger = logging.getLogger(__name__)


class SettingsManager( Singleton ):

    def __init_singleton__( self ):
        self._server_start_datetime = datetimeproxy.now()
        self._subsystem_list = list()
        self._attribute_value_map = dict()
        self._change_listeners = list()
        self._was_initialized = False
        self._attributes_lock = Lock()
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        app_settings_list = self._discover_app_settings()
        self._subsystem_list = self._load_or_create_settings( app_settings_list = app_settings_list )
        self.reload()
        self._was_initialized = True
        return
    
    def reload(self):
        with self._attributes_lock:
            self._attribute_value_map = dict()
            for subsystem in self._subsystem_list:
                subsystem.refresh_from_db()
                for subsystem_attribute in subsystem.attributes.all():
                    attr_type = subsystem_attribute.setting_key
                    self._attribute_value_map[attr_type] = subsystem_attribute.value
                    continue
                continue
            
        self._notify_change_listeners()
        return

    def register_change_listener( self, callback ):
        logger.debug( f'Adding SYSTEM setting change listener from {callback.__module__}' )
        self._change_listeners.append( callback )
        return
    
    def _notify_change_listeners(self):
        for callback in self._change_listeners:
            try:
                callback()
            except Exception as e:
                logger.exception( 'Problem calling setting change callback.', e )
            continue
        return

    def get_server_start_datetime( self ) -> datetime:
        return self._server_start_datetime
    
    def get_subsystems(self) -> List[ Subsystem ]:
        return self._subsystem_list

    def get_setting_value( self, setting_enum : SettingEnum ):
        return self._attribute_value_map.get( setting_enum.key )

    def set_setting_value( self, setting_enum : SettingEnum, value : str ):
        self._attributes_lock.acquire()
        try:
            db_attribute = SubsystemAttribute.objects.get(
                setting_key = setting_enum.key,
            )
            db_attribute.value = value
            db_attribute.save()
            self._attribute_value_map[setting_enum.key] = value  # Just to avoid complete reload of settings

        except SubsystemAttribute.DoesNotExist:
            raise KeyError( f'No setting "{setting_enum.name}"  found.' )
        finally:
            self._attributes_lock.release()
        return

    def _discover_app_settings(self) -> List[ AppSettings ]:

        app_settings_list = list()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi' ):
                continue
            module_name = f'{app_config.name}.settings'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    continue

                app_settings = AppSettings(
                    app_name = app_config.name,
                    app_module = app_module,
                )
                # Needs to have at least one Setting and one SettingDefinition
                if len(app_settings) > 0:
                    app_settings_list.append( app_settings )
                
            except Exception as e:
                logger.exception( f'Problem loading settings for {module_name}.', e )
            continue

        return app_settings_list

    def _load_or_create_settings( self, app_settings_list: List[ AppSettings ] ):
        defined_app_settings_map = { x.app_name: x for x in app_settings_list }
        existing_subsystem_map = {
            x.subsystem_key: x
            for x in Subsystem.objects.prefetch_related('attributes').all()
        }

        subsystem_list = list()
        with transaction.atomic():
            for app_name, app_settings in defined_app_settings_map.items():
                if app_name in existing_subsystem_map:
                    subsystem = self._create_attributes_if_needed(
                        subsystem = existing_subsystem_map[app_name],
                        app_settings = app_settings,
                    )
                else:
                    subsystem = self._create_app_subsystem( app_settings = app_settings )
                subsystem_list.append( subsystem )
                continue
        
        return subsystem_list
    
    def _create_app_subsystem( self, app_settings : AppSettings ):
        
        subsystem = Subsystem.objects.create(
            name = app_settings.label,
            subsystem_key = app_settings.app_name,
        )
        self._create_attributes_if_needed(
            subsystem = subsystem,
            app_settings = app_settings,
        )
        return subsystem

    def _create_attributes_if_needed( self, subsystem : Subsystem, app_settings : AppSettings ):
        all_defined_setting_definitions_map = app_settings.all_setting_definitions()
        existing_setting_keys = { x.setting_key for x in subsystem.attributes.all() }
        
        for setting_key, setting_definition in all_defined_setting_definitions_map.items():
            if setting_key not in existing_setting_keys:
                self._create_setting_attribute(
                    subsystem = subsystem,
                    setting_key = setting_key,
                    setting_definition = setting_definition,
                )
            continue
        return subsystem

    def _create_setting_attribute( self,
                                   subsystem           : Subsystem,
                                   setting_key         : str,
                                   setting_definition  : SettingDefinition ) -> SubsystemAttribute:
        return SubsystemAttribute.objects.create(
            subsystem = subsystem,
            setting_key = setting_key,
            name = setting_definition.label,
            value = setting_definition.initial_value,
            value_type_str = str(setting_definition.value_type),
            value_range_str = setting_definition.value_range_str,
            attribute_type_str = AttributeType.PREDEFINED,
            is_editable = setting_definition.is_editable,
            is_required = setting_definition.is_required,
        )

    
_thread_local = local()


def do_settings_manager_reload():
    logger.debug( 'Reloading SettingsManager from model changes.')
    settings_manager = SettingsManager()
    settings_manager = settings_manager.ensure_initialized()
    settings_manager.reload()
    _thread_local.reload_registered = False
    return


@receiver( post_save, sender = Subsystem )
@receiver( post_save, sender = SubsystemAttribute )
@receiver( post_delete, sender = Subsystem )
@receiver( post_delete, sender = SubsystemAttribute )
def settings_manager_model_changed( sender, instance, **kwargs ):
    """
    Queue the SettingsManager.reload() call to execute after the transaction
    is committed.  This prevents reloading multiple times if multiple
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
        

from datetime import datetime
import logging
from threading import local, Lock
from typing import List

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton

from .models import Subsystem, SubsystemAttribute
from .setting_enums import SettingEnum

logger = logging.getLogger(__name__)


class SettingsManager( Singleton ):

    def __init_singleton__( self ):
        self._server_start_datetime = datetimeproxy.now()
        self._subsystem_list = list()
        self._attribute_value_map = dict()
        self._change_listeners = list()
        self._was_initialized = False
        self._subsystems_lock = Lock()
        self._attributes_lock = Lock()
        return

    def ensure_initialized(self):
        
        with self._subsystems_lock:
            if self._was_initialized:
                return
            self._subsystem_list = self._load_settings()
            
        self.reload()
        self._was_initialized = True
        return
    
    def reload(self):
        with self._attributes_lock:
            self._attribute_value_map = dict()
            for subsystem in self._subsystem_list:
                try:
                    subsystem.refresh_from_db()
                    for subsystem_attribute in subsystem.attributes.all():
                        attr_type = subsystem_attribute.setting_key
                        self._attribute_value_map[attr_type] = subsystem_attribute.value
                        continue
                except Subsystem.DoesNotExist:
                    # Log error - this should not normally happen outside of test teardown
                    logger.error(f'Subsystem {subsystem} no longer exists in database during reload. '
                                 'This may indicate a configuration issue or test teardown problem.')
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
    
    def get_subsystem( self, subsystem_id : int ) -> List[ Subsystem ]:
        for subsystem in self._subsystem_list:
            if subsystem.id == subsystem_id:
                return system
            continue
        raise Subsystem.DoesNotExist()
    
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

    def _load_settings( self ):
        return list( Subsystem.objects.prefetch_related('attributes').all() )

    
_thread_local = local()


def do_settings_manager_reload():
    logger.debug( 'Reloading SettingsManager from model changes.')
    settings_manager = SettingsManager()
    settings_manager.ensure_initialized()
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
        

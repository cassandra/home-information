import logging

from django.db import transaction
from django.apps import apps

logger = logging.getLogger(__name__)


class SettingsInitializer:
    """ Ensure required configured setting DB records exist after migrations are applied. """

    def run( self, sender, **kwargs ):
        logger.debug( 'Populating initial DB records for settings.' )
        app_settings_list = self._discover_app_settings()
        self._create_settings( app_settings_list = app_settings_list )
        return
    
    def _discover_app_settings( self ):
        from hi.apps.common.module_utils import import_module_safe
        from hi.apps.config.app_settings import AppSettings

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

    def _create_settings( self, app_settings_list ):
        with transaction.atomic():
            for app_settings in app_settings_list:
                _ = self._create_app_subsystem_if_needed( app_settings = app_settings )
                continue
        return
    
    def _create_app_subsystem_if_needed( self, app_settings ):
        from hi.apps.config.models import Subsystem

        try:
            subsystem = Subsystem.objects.get( subsystem_key = app_settings.app_name )
        except Subsystem.DoesNotExist:
            subsystem = Subsystem.objects.create(
                name = app_settings.label,
                subsystem_key = app_settings.app_name,
            )
        self._create_attributes_if_needed(
            subsystem = subsystem,
            app_settings = app_settings,
        )
        return subsystem

    def _create_attributes_if_needed( self, subsystem, app_settings ):
        all_defined_setting_definitions_map = app_settings.all_setting_definitions()        
        for setting_key, setting_definition in all_defined_setting_definitions_map.items():
            _ = self._create_setting_attribute_if_needed(
                subsystem = subsystem,
                setting_key = setting_key,
                setting_definition = setting_definition,
            )
            continue
        return

    def _create_setting_attribute_if_needed( self,
                                             subsystem,
                                             setting_key,
                                             setting_definition ):
        from hi.apps.attribute.enums import AttributeType
        from hi.apps.config.models import SubsystemAttribute

        try:
            attribute = SubsystemAttribute.objects.get(
                subsystem = subsystem,
                setting_key = setting_key,
            )
        except SubsystemAttribute.DoesNotExist:
            attribute = SubsystemAttribute.objects.create(
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
        return attribute

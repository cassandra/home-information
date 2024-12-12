from dataclasses import dataclass, field
import logging
from types import ModuleType
from typing import Dict, Iterator, List, Tuple

from hi.apps.common.utils import get_humanized_name
from hi.apps.config.setting_enums import SettingEnum, SettingDefinition

logger = logging.getLogger(__name__)


@dataclass
class AppSettingDefinitions:
    setting_enum            : SettingEnum
    setting_definition_map  : Dict[ str, SettingDefinition ]  # Key is setting key

    def __len__(self):
        return len(self.setting_definition_map)
    
        
class AppSettings:
    """
    Introspects a Django app module to extract the needed attributes to auto-add to
    the system settings.
    """
    
    def __init__( self, app_name : str, app_module : ModuleType ):
        self._app_name = app_name

        self._label = getattr( app_module, 'Label', None )
        if self._label and isinstance( self._label, str ):
            logger.debug( f'Found settings label = "{self._label}" for {app_name}' )
        else:
            self._label = get_humanized_name( name = app_name.split('.')[-1] )
            logger.debug( f'Using default settings label = "{self._label}" for {app_name}' )

        self._app_setting_definitions_list = self._get_app_setting_definitions_list( app_module )
        return

    def __len__(self):
        return len(self._app_setting_definitions_list)

    @property
    def app_name(self):
        return self._app_name

    @property
    def label(self):
        return self._label

    def all_setting_definitions(self) -> Dict[ str, SettingDefinition ]:
        """ Just joins all setting enums together. Index on setting keys which are unique. """
        setting_definition_map = dict()
        for app_setting_definitions in self._app_setting_definitions_list:
            setting_definition_map.update( app_setting_definitions.setting_definition_map )
            continue
        return setting_definition_map
            
    def _get_app_setting_definitions_list( self, app_module : ModuleType ) -> List[ AppSettingDefinitions ]:
        
        app_setting_definitions_list = list()
        for attr_name in dir(app_module):
            attr = getattr( app_module, attr_name )
            if ( isinstance( attr, type )
                 and issubclass( attr, SettingEnum )
                 and attr is not SettingEnum ):
                logger.debug(f'Found Setting subclass for {attr_name}')
                app_setting_definitions = self._get_app_setting_definitions(
                    setting_enum = attr,
                )
                if len(app_setting_definitions) > 0:
                    app_setting_definitions_list.append( app_setting_definitions )
            continue                
        return app_setting_definitions_list

    def _get_app_setting_definitions( self, setting_enum : SettingEnum ) -> AppSettingDefinitions:

        setting_definition_map = dict()
        for setting_name, setting_member in setting_enum.__members__.items():
            logger.debug( f'Adding setting: {setting_member.key}' )
            setting_definition_map[setting_member.key] = setting_member.definition
            continue

        return AppSettingDefinitions(
            setting_enum = setting_enum,
            setting_definition_map = setting_definition_map,
        )


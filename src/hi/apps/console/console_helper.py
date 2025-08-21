import logging

from django.http import HttpRequest

from hi.apps.common.singleton import Singleton
from hi.apps.common.geo_utils import parse_long_lat_from_text, GeoPointParseError
from hi.apps.config.settings_mixins import SettingsMixin
from hi.transient_models import GeographicLocation

from .enums import DisplayUnits
from .constants import ConsoleConstants
from .settings import ConsoleSetting, DEFAULT_LATITUDE, DEFAULT_LONGITUDE

logger = logging.getLogger(__name__)


class ConsoleSettingsHelper( Singleton, SettingsMixin ):

    def __init_singleton__(self):
        self._geo_location_map = dict()
        return

    def get_tz_name( self ) -> str:
        return self.settings_manager().get_setting_value( ConsoleSetting.TIMEZONE )

    def get_geographic_location( self ) -> GeographicLocation:
        geo_location_str = self.settings_manager().get_setting_value( ConsoleSetting.GEO_LOCATION )
        if geo_location_str in self._geo_location_map:
            return self._geo_location_map[geo_location_str]
        try:
            latitude, longitude = parse_long_lat_from_text( geo_location_str )
            geographic_location = GeographicLocation(
                latitude = latitude,
                longitude = longitude,
            )
            self._geo_location_map[geo_location_str] = geographic_location
            return geographic_location
        
        except GeoPointParseError as e:
            logger.error( f'Problem parsing geo location "{geo_location_str}": {e}' )

        return GeographicLocation(
            latitude = DEFAULT_LATITUDE,
            longitude = DEFAULT_LONGITUDE,
        )
            
    def get_sleep_overlay_opacity( self ) -> str:
        return self.settings_manager().get_setting_value( ConsoleSetting.SLEEP_OVERLAY_OPACITY )

    def is_console_locked( self, request : HttpRequest ) -> bool:
        return request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False )
    
    def get_console_lock_password( self ) -> str:
        return self.settings_manager().get_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD )

    def set_console_lock_password( self, password : str ):
        self.settings_manager().set_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD, password )
        return
    
    def get_display_units( self ) -> DisplayUnits:
        display_units_str = self.settings_manager().get_setting_value( ConsoleSetting.DISPLAY_UNITS )
        return DisplayUnits.from_name_safe( display_units_str )
    
    def get_auto_view_enabled( self ) -> bool:
        return self.settings_manager().get_setting_value( ConsoleSetting.AUTO_VIEW_ENABLED ) == 'true'

    def get_auto_view_idle_timeout( self ) -> int:
        return int( self.settings_manager().get_setting_value( ConsoleSetting.AUTO_VIEW_IDLE_TIMEOUT ) )

    def get_auto_view_duration( self ) -> int:
        return int( self.settings_manager().get_setting_value( ConsoleSetting.AUTO_VIEW_DURATION ) )
    

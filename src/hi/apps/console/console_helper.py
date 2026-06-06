import logging
import re
from typing import Dict, Iterable

from django.http import HttpRequest

from hi.apps.common.singleton import Singleton
from hi.apps.common.geo_utils import parse_long_lat_from_text, GeoPointParseError
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.entity.models import Entity
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

    def get_auto_view_duration( self ) -> int:
        return int( self.settings_manager().get_setting_value( ConsoleSetting.AUTO_VIEW_DURATION ) )

    DEFAULT_STATUS_POLLING_INTERVAL_MS = 3000

    def get_status_polling_interval_ms( self ) -> int:
        # Stored in seconds (user-friendly); the client contract is in ms.
        # Robust to an uninitialized/blank setting so the per-request
        # context processor can call this unconditionally.
        raw_value = self.settings_manager().get_setting_value( ConsoleSetting.STATUS_POLLING_INTERVAL )
        try:
            return int( raw_value ) * 1000
        except ( TypeError, ValueError ):
            return self.DEFAULT_STATUS_POLLING_INTERVAL_MS

    @staticmethod
    def compute_camera_short_names( entity_list : Iterable[ Entity ] ) -> Dict[ int, str ]:
        """Return a ``{entity.id: short_name}`` mapping for camera-button
        labels. Heuristic, operating on the full displayed set so the
        label can honor cross-entity context:

        1. Strip whole-word "camera" tokens (case-insensitive) and
           collapse intermediate whitespace. As a follow-up suffix
           pass, also strip a trailing "camera" (case-insensitive, with
           or without a preceding space) when the original name is at
           least 9 characters -- catches concatenated forms like
           "BackdoorCamera" the word-boundary regex misses, while the
           length floor avoids reducing short names like "MyCamera"
           to a 2-letter label.
        2. If two or more entities share a leading whole-word token,
           strip that common token-prefix from each. Only applied when
           every per-entity result remains non-empty after stripping;
           otherwise the prefix-strip is skipped for the whole set.

        Single-entity inputs (or no shared leading token) get only the
        per-entity "camera"-token strip — no global awareness needed.
        Empty short names are never produced; if both passes would
        yield empty, the falls-back result is the entity's stripped
        name (or the original if even that is empty after stripping).
        """
        def strip_camera_tokens( name : str ) -> str:
            cleaned = re.sub( r'\bcamera\b', '', name, flags = re.IGNORECASE )
            cleaned = re.sub( r'\s+', ' ', cleaned ).strip()
            if len( name ) >= 9 and cleaned.lower().endswith( 'camera' ):
                cleaned = cleaned[ :-6 ].rstrip()
            return cleaned

        stripped : Dict[ int, str ] = {
            e.id: strip_camera_tokens( e.name ) or e.name for e in entity_list
        }

        token_lists = [ s.split() for s in stripped.values() ]
        common_prefix : list = []
        if len( token_lists ) >= 2 and all( token_lists ):
            for tokens in zip( *token_lists ):
                if len( set( tokens ) ) == 1:
                    common_prefix.append( tokens[ 0 ] )
                else:
                    break

        if common_prefix:
            prefix_len = len( common_prefix )
            candidates = {
                eid: ' '.join( s.split()[ prefix_len: ] ) for eid, s in stripped.items()
            }
            if all( candidates.values() ):
                return candidates

        return stripped

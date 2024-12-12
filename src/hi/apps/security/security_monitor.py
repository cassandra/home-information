import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.console.settings import ConsoleSetting
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .enums import SecurityState
from .security_manager import SecurityManager
from .settings import SecuritySetting

logger = logging.getLogger(__name__)


class SecurityMonitor( PeriodicMonitor ):

    SECURITY_POLLING_INTERVAL_SECS = 5 * 60

    def __init__( self ):
        super().__init__(
            id = 'security-monitor',
            interval_secs = self.SECURITY_POLLING_INTERVAL_SECS,
        )
        self._security_manager = SecurityManager()
        self._last_security_state_check_datetime = datetimeproxy.now()
        return

    async def do_work(self):
        await self._check_security_state()
        return

    async def _check_security_state( self ):
        logger.debug( 'Checking security state.' )
        settings_manager = SettingsManager()
        current_datetime = datetimeproxy.now()
        tz_name = settings_manager.get_setting_value(
            ConsoleSetting.TIMEZONE,
        )
        try:
            # Some states do not allow automated changes
            if not self._security_manager.security_state.auto_change_allowed:
                return

            day_start_time_of_day = settings_manager.get_setting_value(
                SecuritySetting.SECURITY_DAY_START,
            )
            if datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = day_start_time_of_day,
                    tz_name = tz_name,
                    start_datetime = self._last_security_state_check_datetime,
                    end_datetime = current_datetime ):
                logger.debug( 'Security state check: Setting as DAY.' )
                self._security_manager.update_security_state_auto(
                    new_security_state = SecurityState.DAY,
                )
                return

            night_start_time_of_day = settings_manager.get_setting_value(
                SecuritySetting.SECURITY_NIGHT_START,
            )
            if datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = night_start_time_of_day,
                    tz_name = tz_name,
                    start_datetime = self._last_security_state_check_datetime,
                    end_datetime = current_datetime ):
                logger.debug( 'Security state check: Setting as NIGHT.' )
                self._security_manager.update_security_state_auto(
                    new_security_state = SecurityState.NIGHT,
                )
                return
            
        finally:
            self._last_security_state_check_datetime = current_datetime
        return

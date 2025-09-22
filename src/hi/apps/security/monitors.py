import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .enums import SecurityState
from .security_mixins import SecurityMixin
from .settings import SecuritySetting

logger = logging.getLogger(__name__)


class SecurityMonitor( PeriodicMonitor, SettingsMixin, SecurityMixin ):

    MONITOR_ID = 'hi.apps.security.monitor'
    SECURITY_POLLING_INTERVAL_SECS = 5

    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.SECURITY_POLLING_INTERVAL_SECS,
        )
        self._last_security_state_check_datetime = datetimeproxy.now()
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Security Monitor',
            description = 'Security state monitoring',
            expected_heartbeat_interval_secs = cls.SECURITY_POLLING_INTERVAL_SECS,
        )

    async def do_work(self):
        try:
            message = await self._check_security_state()
            self.record_healthy(message)
        except Exception as e:
            error_msg = f"Security state check failed: {str(e)[:50]}"
            logger.exception(error_msg)
            self.record_error(error_msg)
        return

    async def _check_security_state( self ) -> str:
        """Check security state and return status message."""
        logger.debug( 'Security monitor: Checking security state.' )
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return "Settings manager not available"
        security_manager = await self.security_manager_async()
        if not security_manager:
            return "Security manager not available"

        current_datetime = datetimeproxy.now()
        tz_name = ConsoleSettingsHelper().get_tz_name()
        current_state = security_manager.security_state

        try:
            # Some states do not allow automated changes
            if not current_state.auto_change_allowed:
                logger.debug( f'Security state "{current_state}". Auto-change not allowed.' )
                return f"Auto-change blocked ({current_state.label} mode)"

            day_start_time_of_day = settings_manager.get_setting_value(
                SecuritySetting.SECURITY_DAY_START,
            )
            if datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = day_start_time_of_day,
                    tz_name = tz_name,
                    start_datetime = self._last_security_state_check_datetime,
                    end_datetime = current_datetime ):
                logger.debug( 'Security state check: Setting as DAY.' )
                security_manager.update_security_state_auto(
                    new_security_state = SecurityState.DAY,
                )
                return f"Transitioned {current_state.label} → Day"

            night_start_time_of_day = settings_manager.get_setting_value(
                SecuritySetting.SECURITY_NIGHT_START,
            )
            if datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = night_start_time_of_day,
                    tz_name = tz_name,
                    start_datetime = self._last_security_state_check_datetime,
                    end_datetime = current_datetime ):
                logger.debug( 'Security state check: Setting as NIGHT.' )
                security_manager.update_security_state_auto(
                    new_security_state = SecurityState.NIGHT,
                )
                return f"Transitioned {current_state.label} → Night"

            logger.debug( 'Security monitor: No change needed.' )
            return f"No change needed ({current_state.label} mode)"
        finally:
            self._last_security_state_check_datetime = current_datetime

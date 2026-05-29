import logging

from asgiref.sync import sync_to_async
from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.enums import AlarmLevel
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.system.provider_info import ProviderInfo
from hi.testing.dev_overrides import DevOverrideManager

from .constants import HassTimeouts
from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassMonitor( PeriodicMonitor, HassMixin, SensorResponseMixin ):

    MONITOR_ID = 'hi.services.hass.monitor'

    def __init__( self ):
        super().__init__( id = self.MONITOR_ID )
        self._was_initialized = False
        return

    def get_polling_interval_secs(self) -> int:
        # The framework calls this at sort time (before _initialize
        # has run ``await self.hass_manager_async()`` and cached the
        # manager reference on this instance), and on every tick
        # after that. Use the manager's reloaded value when the
        # mixin's cached ``_hass_manager`` attribute exists; fall
        # back to the static constant before then -- avoids
        # triggering the manager mixin's sync ``ensure_initialized``
        # from the async event-loop thread.
        if hasattr( self, '_hass_manager' ):
            return self._hass_manager.polling_interval_secs
        return HassTimeouts.POLLING_INTERVAL_SECS

    def get_api_timeout(self) -> float:
        return HassTimeouts.API_TIMEOUT_SECS

    def alarm_ceiling(self):
        # HA outage in the background masks security and home-automation
        # state changes. Treat health failures here as serious.
        return AlarmLevel.CRITICAL

    async def _initialize(self):
        hass_manager = await self.hass_manager_async()
        if not hass_manager:
            return
        _ = await self.sensor_response_manager_async()  # Allows async use of self.sensor_response_manager()
        hass_manager.register_change_listener( self.refresh )
        # Register this monitor as a subordinate health source on the
        # manager so the manager's aggregated health reflects monitor
        # outcomes. The manager pulls our current status on each read of
        # its health_status; we never push.
        hass_manager.add_subordinate_health_status_provider( self )
        self._was_initialized = True
        return
    
    def refresh( self ):
        """ 
        Called when integration settings are changed (via listener callback).
        
        Note: HassManager.reload() is already called BEFORE this callback is triggered,
        so we should NOT call manager.reload() here to avoid redundant reloads.
        The monitor should just reset its own state to pick up fresh manager state.
        """
        # Reset monitor state so next cycle reinitializes with updated manager
        self._was_initialized = False
        logger.info( 'HassMonitor refreshed - will reinitialize with new settings on next cycle' )
        return
        
    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Home Assistant Monitor',
            description = 'Home Assistant device state monitoring',
        )

    async def do_work(self):
        if not self._was_initialized:
            await self._initialize()

        if not self._was_initialized:
            # Timing issues when first enabling could fail initialization.
            logger.warning( 'HAss monitor failed to initialize. Skipping work cycle.' )
            self.record_warning( 'Was not initialized.' )
            return
        
        hass_manager = await self.hass_manager_async()
        if not hass_manager:
            self.record_error( 'No manager found.' )
            return
        
        id_to_hass_state_map = await hass_manager.fetch_hass_states_from_api_async( verbose = False )
        logger.debug( f'Fetched {len(id_to_hass_state_map)} HAss States' )

        hass_manager.update_latest_attrs_cache( id_to_hass_state_map )

        current_datetime = datetimeproxy.now()
        sensor_response_latest_map = dict()
        
        # The converter chain is sync; the IntegrationMetadataCache it
        # consults may trigger DB queries on cold-cache or new-entity
        # paths. Wrap each per-state translation through sync_to_async
        # so any DB work happens in a thread pool rather than raising
        # SynchronousOnlyOperation in this async monitor context.
        translate = sync_to_async(
            HassConverter.hass_state_to_sensor_value_map,
            thread_sensitive = True,
        )
        for hass_state in id_to_hass_state_map.values():
            value_map = await translate( hass_state )
            if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                DevOverrideManager.trace_state(
                    'hi.ha_poll.in',
                    integration_name = hass_state.entity_id,
                    integration_value = hass_state.state_value,
                    device_class = hass_state.device_class,
                    value_map = { str(k): v for k, v in value_map.items() },
                )
            for integration_key, sensor_value_str in value_map.items():
                if not sensor_value_str:
                    continue
                sensor_response = SensorResponse(
                    integration_key = integration_key,
                    value = sensor_value_str,
                    timestamp = current_datetime,
                )
                sensor_response_latest_map[integration_key] = sensor_response
                continue
            continue

        await self.sensor_response_manager().update_with_latest_sensor_responses(
            sensor_response_map = sensor_response_latest_map,
        )

        message = f'Processed {len(id_to_hass_state_map)} Home Assistant states.'
        self.record_healthy( message )
        # Manager picks up our status via add_subordinate_health_status_provider
        # registration; no explicit push needed here.
        return
    

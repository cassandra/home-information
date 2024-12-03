import logging
import re

from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.transient_models import IntegrationControlResult

from .zm_manager import ZoneMinderManager

logger = logging.getLogger(__name__)


class ZoneMinderController( IntegrationController ):

    def __init__(self):
        self._zm_manager = ZoneMinderManager()
        return
    
    def do_control( self,
                    integration_key  : IntegrationKey,
                    control_value    : str             ) -> IntegrationControlResult:
        try:
            if integration_key.integration_name == self._zm_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME:
                return self.set_run_state( run_state_value = control_value )

            if integration_key.integration_name.startswith( self._zm_manager.MONITOR_FUNCTION_SENSOR_PREFIX ):
                m = re.match( r'.+\D(\d+)', integration_key.integration_name )
                if m:
                    return self.set_monitor_function(
                        monitor_id = m.group(1),
                        function_value = control_value,
                    )

            logger.warning( f'ZM action undefined. key={integration_key}, value={control_value}' )
            raise ValueError( 'Unknown ZM control action.' )

        except Exception as e:
            logger.warning( f'Exception in ZM do_control: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str(e) ],
            )
        finally:
            self._zm_manager.clear_caches()

    def set_run_state( self, run_state_value : str ):
        response = self._zm_manager._zm_client.set_state( run_state_value )
        logger.debug( f'ZM Set run state to "{run_state_value}" = {response}' )
        return IntegrationControlResult(
            new_value = run_state_value,
            error_list = [],
        )

    def set_monitor_function( self,
                              monitor_id      : str,
                              function_value  : str ):
        zm_monitor_list = self._zm_manager.get_zm_monitors()
        for zm_monitor in zm_monitor_list:
            if str(zm_monitor.id()) == str(monitor_id):
                response = zm_monitor.set_parameter({
                    'function': function_value,
                })
                logger.debug( f'ZM Set monitor: {monitor_id}={function_value}, response={response}' )
                response_message = response.get('message')
                if response_message and ( 'error' in response_message.lower() ):
                    raise ValueError( 'Problen setting ZM monitor function.')

                return IntegrationControlResult(
                    new_value = function_value,
                    error_list = [],
                )
            else:
                logger.debug( f'Skipping ZM monitor: {zm_monitor.id()} != {monitor_id}' )
            continue

        raise ValueError( 'Unknown ZM entity.')

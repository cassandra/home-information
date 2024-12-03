import logging
import re

from hi.apps.common.processing_result import ProcessingResult

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

        if integration_key.integration_name == self._zm_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME:
            return self.set_run_state( run_state_value = control_value )
        
        if integration_key.integration_name.startswith( self._zm_manager.MONITOR_FUNCTION_SENSOR_PREFIX ):
            m = re.match( r'.+\D(\d+)', integration_key.integration_name )
            if m:
                return self.set_monitor_function(
                    monitor_id = m.group(1),
                    function_value = control_value,
                )
            
        logger.warning( f'Unknown ZM control action. key={integration_key}, value={control_value}' )
        return IntegrationControlResult(
            new_value = None,
            error_messages = [ 'Unknown ZM control action.' ]
        )

    def set_run_state( self, run_state_value : str ):
        result = ProcessingResult( title = 'ZM Set Monitors' )
        try:
            response = self._zm_manager._zm_client.set_state( run_state_value )
            logger.debug( f'ZM Set run state to "{run_state_value}" = {response}' )
            return IntegrationControlResult(
                new_value = run_state_value,
                processing_result = result,
            )
        except Exception as e:
            logger.error( f'Exception setting ZM run state: {e}' )
            result.error_list.append( str(e) )
            return IntegrationControlResult(
                new_value = None,
                processing_result = result,
            )
        finally:
            self._zm_manager.clear_caches()

    def set_monitor_function( self,
                              monitor_id      : str,
                              function_value  : str ):
        result = ProcessingResult( title = 'ZM Set Monitor Function' )
        try:
            zm_monitor_list = self._zm_manager.get_zm_monitors()
            for zm_monitor in zm_monitor_list:
                if str(zm_monitor.id()) == str(monitor_id):
                    response = zm_monitor.set_parameter({
                        'function': function_value,
                    })
                    logger.debug( f'ZM Set monitor: {monitor_id}={function_value}, response={response}' )
                    response_message = response.get('message')
                    if response_message and ( 'error' in response_message.lower() ):
                        result.error_list.append( 'Problen setting ZM monitor function.')
                    return IntegrationControlResult(
                        new_value = function_value,
                        processing_result = result,
                    )
                else:
                    logger.debug( f'Skipping ZM monitor: {zm_monitor.id()} != {monitor_id}' )
                continue

            result.error_list.append( 'Unknown ZM monitor.')
            return IntegrationControlResult(
                new_value = None,
                processing_result = result,
            )
        except Exception as e:
            logger.error( f'Exception setting ZM monitor function: {e}' )
            result.error_list.append( str(e) )
            return IntegrationControlResult(
                new_value = None,
                processing_result = result,
            )
        finally:
            self._zm_manager.clear_caches()

from datetime import datetime
import json
import logging
import pytz
from urllib.parse import unquote
from typing import Dict, Any

from django.core.exceptions import BadRequest
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.zoneminder.constants import ZmSimConstants
from hi.simulator.services.zoneminder.enums import ZmMonitorFunction
from hi.simulator.services.zoneminder.simulator import ZoneMinderSimulator
from hi.simulator.services.zoneminder.sim_models import ZmPagination
from hi.simulator.services.zoneminder.zm_event_manager import ZmSimEventManager

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class HostLoginView( View ):

    def post(self, request, *args, **kwargs):
        response_data = {
            'credentials': 'auth=f5b9cf48693fe8552503c8ABCD5',
            'append_password': 0,
            'version': '1.36.12',
            'apiversion': '1.0',
        }
        return JsonResponse(response_data)

    
@method_decorator(csrf_exempt, name='dispatch')
class HostVersionView( View ):

    def get(self, request, *args, **kwargs):
        response_data = {
            'version': '1.36.12',
        }
        return JsonResponse(response_data)

    
@method_decorator(csrf_exempt, name='dispatch')
class MonitorsView( View ):

    def get(self, request, *args, **kwargs):
        try:
            zm_simulator = ZoneMinderSimulator()
            zm_monitor_sim_entity_list = zm_simulator.get_zm_monitor_sim_entity_list()
            return JsonResponse({
                'monitors': [ x.to_api_dict() for x in zm_monitor_sim_entity_list ],
            })
        except Exception as e:
            logger.exception( 'Problem processing ZM monitors API request', e )
            return JsonResponse({
                'monitors': [ ],
            })
 
    def post(self, request, *args, **kwargs):
        try:
            monitor_id = int( kwargs.get('monitor_id'))
            monitor_function_str = request.POST.get('Monitor[Function]')
            if not monitor_function_str:
                raise BadRequest( 'Request missing monitor function data.' )
            logger.debug( f'ZM set monitor function: {monitor_id} = {request.POST}' )

            zm_monitor_function = ZmMonitorFunction.from_value( monitor_function_str )
            zm_simulator = ZoneMinderSimulator()
            _ = zm_simulator.set_monitor_function( 
                monitor_id = monitor_id,
                zm_monitor_function = zm_monitor_function,
            )
            return JsonResponse(
                {
                    "status": "success",
                    "monitor_function": monitor_function_str,
                },
                safe = False,
            )
        
        except json.JSONDecodeError as jde:
            raise BadRequest( f'Request body is not JSON: {jde}' )

        except ValueError as ve:
            raise BadRequest( f'Unknown ZoneMinder monitor function: {ve}' )

        except KeyError as ke:
            raise BadRequest( f'Unknown ZoneMinder monitor: {ke}' )


class StatesView( View ):

    def get(self, request, *args, **kwargs):
        try:
            zm_simulator = ZoneMinderSimulator()
            zm_sim_run_state_list = zm_simulator.get_zm_sim_run_state_list()
            return JsonResponse({
                'states': [ x.to_api_dict() for x in zm_sim_run_state_list ],
            })
        except Exception as e:
            logger.exception( 'Problem processing ZM states API request', e )
            return JsonResponse({
                'states': [ ],
            })
        

class EventsIndexView( View ):

    def get(self, request, *args, **kwargs):
        try:
            event_filter = kwargs.get('filter')
            filter_dict = self.parse_event_filter( event_filter = event_filter )

            if (( 'StartTime' not in filter_dict )
                or ( len(filter_dict) != 1 )):
                raise BadRequest( 'StartTime event filtering is only currently supported' )

            start_time_filter = filter_dict.get( 'StartTime' )
            filter_operator = start_time_filter.get( 'operator' )
            filter_value_datetime = start_time_filter.get( 'value_datetime' )
            
            if filter_operator != '>=':
                raise BadRequest( 'Only ">=" event filter operator is currently supported.' )
            
            zm_event_manager = ZmSimEventManager()
            zm_sim_run_state_list = zm_event_manager.get_events_by_start_datetime(
                start_datetime = filter_value_datetime,
            )
            zm_pagination = ZmPagination(
                page = 1,
            )
            return JsonResponse({
                'events': [ x.to_api_dict() for x in zm_sim_run_state_list ],
                'pagination': zm_pagination.to_api_dict(),

            })
        except Exception as e:
            logger.exception( 'Problem processing ZM events API request', e )
            return JsonResponse({
                'events': [ ],
                'pagination': ZmPagination( page = 1 ).to_api_dict(),
            })

    def parse_event_filter( self, event_filter: str) -> Dict[str, Any]:
        """
        Parses a ZoneMinder-style event filter string into a dictionary.

        Args:
            event_filter (str): The URL-encoded filter string (e.g., "StartTime%20%3E=:2025-01-16%2012:18:53").

        Returns:
            Dict[str, Any]: A dictionary with filter keys and their parsed operations and values.
        """
        tz = pytz.timezone( ZmSimConstants.TIMEZONE_NAME )
        
        filters = {}
        decoded_filter = unquote(event_filter)
        filter_parts = decoded_filter.split(',')

        for part in filter_parts:
            if ':' in part:
                key_operator, value = part.split( ':', 1 )

                if '>' in key_operator:
                    key, operator = key_operator.split( '>', 1 )
                    operator = '>' + operator
                elif '<' in key_operator:
                    key, operator = key_operator.split( '<', 1 )
                    operator = '<' + operator
                elif '=' in key_operator:
                    key, operator = key_operator.split( '=', 1 )
                    operator = '=' + operator
                else:
                    raise ValueError(f"Invalid filter format: {part}")

                try:
                    value_datetime = tz.localize( datetime.strptime( value.strip(), "%Y-%m-%d %H:%M:%S" ))
                    filters[key.strip()] = {
                        'operator': operator.strip(),
                        'value_datetime': value_datetime,
                    }
                except ValueError as ve:
                    logger.exception( f'Problem parsing filter date: {value}', ve )
                    continue
                

        return filters

from datetime import timedelta
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.simulator.services.zoneminder.simulator import ZoneMinderSimulator

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
        pass


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
        return JsonResponse({
            'events': [ ],
            'pagination': {
                'page': 1,
                'current': 1,
                'count': 1,
                'prevPage': False,
                'nextPage': False,
                'pageCount': 1,
                'order': {
                    'Event.StartTime': 'desc'
                },
                'limit': 100,
                'options': {
                    'order': {
                        'Event.StartTime': 'desc'
                    },
                    'sort': 'StartTime',
                    'direction': 'desc'
                },
                'paramType': 'querystring',
                'queryScope': None,
            },
            
        })
    








        
        zm_monitor = ZmMonitor(
            id = 1,
            name = 'SideCamera',
        )

        start_ago_secs = 45
        end_ago_secs = 39
        start_datetime = datetimeproxy.now() - timedelta( seconds = start_ago_secs )
        end_datetime = datetimeproxy.now() - timedelta( seconds = end_ago_secs )
        zm_event = ZmEvent(
            zm_monitor = zm_monitor,
            event_id = 1,
            start_datetime = start_datetime,
            end_datetime = end_datetime,
            name = 'Event 1',
            cause = 'Hardcoded',
            length_secs = 5.5,
            total_frames = 15,
            alarm_frames = 6,
            total_score = 123,
            average_score = 85,
            max_score = 140,
        )
        zm_pagination = ZmPagination(
            page = 1,
        )
        return JsonResponse({
            'events': [ zm_event.to_api_dict() ],
            'pagination': zm_pagination.to_api_dict(),

        })
    

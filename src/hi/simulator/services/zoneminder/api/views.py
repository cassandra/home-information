from datetime import timedelta

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy

from .transient_models import ZmEvent, ZmMonitor, ZmPagination, ZmState


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
        zm_monitor = ZmMonitor(
            id = 1,
            name = 'SideCamera',
        )
        return JsonResponse({
            'monitors': [ zm_monitor.to_api_dict() ],
        })

    def post(self, request, *args, **kwargs):
        pass


class StatesView( View ):

    def get(self, request, *args, **kwargs):
        zm_state = ZmState(
            id = 1,
            name = 'default',
            definition_list = [],
            is_active = True,
        )
        return JsonResponse({
            'states': [ zm_state.to_api_dict() ],
        })


class EventsIndexView( View ):

    def get(self, request, *args, **kwargs):
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
    

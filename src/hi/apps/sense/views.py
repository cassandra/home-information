import logging

from django.urls import reverse
from django.views.generic import View

from hi.hi_async_view import HiModalView
from hi.apps.common.pagination import compute_pagination_from_queryset

from .models import SensorHistory
from .view_mixin import SenseViewMixin

logger = logging.getLogger(__name__)


class SensorHistoryView( HiModalView, SenseViewMixin ):

    SENSOR_HISTORY_PAGE_SIZE = 25
    
    def get_template_name( self ) -> str:
        return 'sense/modals/sensor_history.html'

    def get( self, request, *args, **kwargs ):

        sensor = self.get_sensor( request, *args, **kwargs )
        base_url = reverse( 'sense_sensor_history', kwargs = { 'sensor_id': sensor.id } )

        queryset = SensorHistory.objects.filter( sensor = sensor )
        pagination = compute_pagination_from_queryset( request = request,
                                                       queryset = queryset,
                                                       base_url = base_url,
                                                       page_size = self.SENSOR_HISTORY_PAGE_SIZE,
                                                       async_urls = True )
        sensor_history_list = queryset[pagination.start_offset:pagination.end_offset + 1]

        context = {
            'sensor': sensor,
            'sensor_history_list': sensor_history_list,
            'pagination': pagination,
        }
        return self.modal_response( request, context )

        
class SensorHistoryDetailsView( View, SenseViewMixin ):

    def get(self, request, *args, **kwargs):
        pass

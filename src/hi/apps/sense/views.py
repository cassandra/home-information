import logging

from django.urls import reverse

from hi.apps.common.pagination import compute_pagination_from_queryset

from hi.hi_async_view import HiModalView

from .models import SensorHistory
from .view_mixins import SenseViewMixin

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


class SensorHistoryDetailsView( HiModalView, SenseViewMixin ):

    def get_template_name( self ) -> str:
        return 'sense/modals/sensor_history_details.html'
    
    def get(self, request, *args, **kwargs):
        sensor_history = self.get_sensor_history( request, *args, **kwargs )
        
        # Create SensorResponse from sensor_history for video URL generation
        sensor_response = None
        try:
            from .transient_models import SensorResponse
            sensor_response = SensorResponse.from_sensor_history(sensor_history)
        except Exception as e:
            logger.error(f"Error creating SensorResponse from sensor_history: {e}")
        
        context = {
            'sensor_history': sensor_history,
            'sensor_response': sensor_response,
        }
        return self.modal_response( request, context )

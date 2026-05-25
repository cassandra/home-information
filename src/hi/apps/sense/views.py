import logging

from hi.hi_async_view import HiModalView

from .transient_models import SensorResponse
from hi.apps.sense.view_mixins import SenseViewMixin

logger = logging.getLogger(__name__)


class SensorHistoryDetailsView( HiModalView, SenseViewMixin ):

    def get_template_name( self ) -> str:
        return 'sense/modals/sensor_history_details.html'

    def get(self, request, *args, **kwargs):
        sensor_history = self.get_sensor_history( request, *args, **kwargs )

        # Create SensorResponse from sensor_history for video URL generation
        sensor_response = None
        try:
            sensor_response = SensorResponse.from_sensor_history(sensor_history)
        except Exception as e:
            logger.error(f"Error creating SensorResponse from sensor_history: {e}")

        context = {
            'sensor_history': sensor_history,
            'sensor_response': sensor_response,
        }
        return self.modal_response( request, context )

from django.core.exceptions import BadRequest
from django.http import Http404

from hi.apps.sense.models import Sensor, SensorHistory


class SenseViewMixin:

    def get_sensor( self, request, *args, **kwargs ) -> Sensor:
        """ Assumes there is a required sensor_id in kwargs """
        try:
            sensor_id = int( kwargs.get( 'sensor_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid sensor id.' )
        try:
            return Sensor.objects.get( id = sensor_id )
        except Sensor.DoesNotExist:
            raise Http404( request )

    def get_sensor_history( self, request, *args, **kwargs ) -> SensorHistory:
        """ Assumes there is a required id in kwargs """
        try:
            sensor_history_id = int( kwargs.get( 'sensor_history_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid sensor history id.' )
        try:
            return SensorHistory.objects.select_related('sensor').get( id = sensor_history_id )
        except SensorHistory.DoesNotExist:
            raise Http404( request )

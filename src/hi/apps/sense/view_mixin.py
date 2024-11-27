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

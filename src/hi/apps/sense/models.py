from django.db import models

from hi.apps.entity.models import EntityState
from hi.integrations.core.models import IntegrationKeyModel

from .enums import SensorType


class Sensor( IntegrationKeyModel ):
    """
    - Represents an observed state of an entity.
    - Will sense exactly one EntityState
    """
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    entity_state = models.ForeignKey(
        EntityState,
        related_name = 'sensors',
        verbose_name = 'Entity State',
        on_delete = models.CASCADE,
    )
    sensor_type_str = models.CharField(
        'Sensor Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Sensor'
        verbose_name_plural = 'Sensors'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'integration_id', 'integration_name' ],
                name = 'sensor_integration_key',
            ),
        ]
        
    @property
    def sensor_type(self):
        return SensorType.from_name_safe( self.sensor_type_str )

    @sensor_type.setter
    def sensor_type( self, sensor_type : SensorType ):
        self.sensor_type_str = str(sensor_type)
        return

    
class SensorHistory(models.Model):

    sensor = models.ForeignKey(
        Sensor,
        related_name = 'history',
        verbose_name = 'Sensor',
        on_delete = models.CASCADE,
    )
    value = models.CharField(
        'Value',
        max_length = 255
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    
    class Meta:
        verbose_name = 'Sensor History'
        verbose_name_plural = 'Sensor History'

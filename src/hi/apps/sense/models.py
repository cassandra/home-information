from django.db import models

from hi.apps.entity.models import Entity, EntityState

from .enums import SensorType


class Sensor( models.Model ):
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
        on_delete=models.CASCADE,
    )
    sensor_type_str = models.CharField(
        'Sensor Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Sensor'
        verbose_name_plural = 'Sensors'

    @property
    def sensor_type(self):
        return SensorType.from_name_safe( self.sensor_type_str )

    @sensor_type.setter
    def sensor_type( self, sensor_type : SensorType ):
        self.sensor_type_str = str(sensor_type)
        return

    
class SensedEntity(models.Model):
    """The Entity associated with a Sensors's state is implicitly a
    "sensed" entity, but this may also be sensing (directly or
    indirectly) the state of more than one entity.

    e.g., An open/close sensor is directly sensing the proximity sensor in
    the device, but it is indirectly trying to sense the state of a door or window.

    e.g., A temperature sensor might be the aggregate of a number of thermometer readings.

    """

    sensor = models.ForeignKey(
        Sensor,
        related_name = '+',
        verbose_name = 'Sensor',
        on_delete=models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'sensed_by',
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    
    class Meta:
        verbose_name = 'Sensed Entity'
        verbose_name_plural = 'Sensed Entities'

        
class SensorHistory(models.Model):

    sensor = models.ForeignKey(
        Sensor,
        related_name = 'history',
        verbose_name = 'Sensor',
        on_delete=models.CASCADE,
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

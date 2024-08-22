from django.db import models

from hi.apps.devices.models import DeviceState

from .enums import SensorType, SensedAreaType


class Sensor( models.Model ):
    """
    - Represents an observed state of an device.
    - An devices state's is hidden and a sensor's value may not be true state (sensors can fail).
    - May sense zero or more Entities
    - When sensing multiple Entities, the sensed value is a single value, aggregated from all.
    - The SensorType defines the type of sensed value.
    - Sensor value are discrete, continuous or a blob a data.
    - Continuous valued sensors usually have units (defined by the SensorType).
    """
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    device_state = models.ForeignKey(
        DeviceState,
        related_name = 'sensors',
        verbose_name = 'Device State',
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
    

# !!! Not a thing anymore: state variables this senses are related to areas
class SensedEntity(models.Model):

    sensor = models.ForeignKey(
        Sensor,
        related_name = 'sensed_entities',
        verbose_name = 'Sensor',
        on_delete=models.CASCADE,
    )
    sensed_entity = models.ForeignKey(
        Entity,
        related_name = 'sense_sources',
        verbose_name = 'Sensed Entity',
        on_delete=models.CASCADE,
    )
    
    class Meta:
        verbose_name = 'Sensed Entity'
        verbose_name_plural = 'Sensed Entities'

        
# !!! Not a thing anymore: state variables this senses are related to areas
class SensedArea(models.Model):
    """For sensors that are detection area-wide conditions. The SVG styling
    will come from the SensedAreaType.

    """


    # ????  !!! Not needed if an entity can be an Area?

    
    sensor = models.ForeignKey(
        Entity,
        related_name = 'sensed_areas',
        verbose_name = 'Sensor',
        on_delete=models.CASCADE,
    )
    svg_path = models.TextField(
        'Path',
        null = False, blank = False,
    )
    sensed_area_type_str = models.CharField(
        'Sensed Area Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Sensed Area'
        verbose_name_plural = 'Sensed Areas'

    @property
    def sensed_area_type(self):
        return SensedAreaType.from_name_safe( self.sensed_area_type_str )

    @sensed_area_type.setter
    def sensed_area_type( self, sensed_area_type : SensedAreaType ):
        self.sensed_area_type_str = str(sensed_area_type)
        return


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
    

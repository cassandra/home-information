from django.db import models

from hi.apps.entity.models import Entity

from .enums import SensorType, SensedAreaType


class Sensor( models.Model ):

    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'sensors',
        verbose_name = 'Entity',
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

    sensor = models.ForeignKey(
        Entity,
        related_name = 'sensed_entities',
        verbose_name = 'Sensor',
        on_delete=models.CASCADE,
    )
    sensed_entity = models.ForeignKey(
        Entity,
        related_name = 'sensing_source',
        verbose_name = 'Sensed Entity',
        on_delete=models.CASCADE,
    )
    
    class Meta:
        verbose_name = 'Sensed Entity'
        verbose_name_plural = 'Sensed Entities'

        
class SensedArea(models.Model):
    """For sensors that are detection area-wide conditions. The SVG styling
    will come from the SensedAreaType.

    """
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

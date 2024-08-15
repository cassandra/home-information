from django.db import models

from hi.apps.entity.models import Entity

from .enums import ControlType, ControlledAreaType


class Control( models.Model ):

    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'controls',
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    control_type_str = models.CharField(
        'Control Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Control'
        verbose_name_plural = 'Controls'

    @property
    def control_type(self):
        return ControlType.from_name_safe( self.control_type_str )

    @control_type.setter
    def control_type( self, control_type : ControlType ):
        self.control_type_str = str(control_type)
        return

    
class ControlledEntity(models.Model):

    control = models.ForeignKey(
        Entity,
        related_name = 'controlled_entities',
        verbose_name = 'Control',
        on_delete=models.CASCADE,
    )
    controlled_entity = models.ForeignKey(
        Entity,
        related_name = 'controlling_source',
        verbose_name = 'Controlled Entity',
        on_delete=models.CASCADE,
    )
    
    class Meta:
        verbose_name = 'Controlled Entity'
        verbose_name_plural = 'Controlled Entities'

        
class ControlledArea(models.Model):
    """For controls that exert influence over an area. The SVG styling will
    come from the ControlledAreaType.

    """
    
    control = models.ForeignKey(
        Entity,
        related_name = 'controlled_areas',
        verbose_name = 'Control',
        on_delete=models.CASCADE,
    )
    svg_path = models.TextField(
        'Path',
        null = False, blank = False,
    )
    controlled_area_type_str = models.CharField(
        'Control Area Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Controlled Area'
        verbose_name_plural = 'Controlled Areas'

    @property
    def controlled_area_type(self):
        return ControlledAreaType.from_name_safe( self.controlled_area_type_str )

    @controlled_area_type.setter
    def controlled_area_type( self, controlled_area_type : ControlledAreaType ):
        self.controlled_area_type_str = str(control_coverage_type)
        return

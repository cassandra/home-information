from django.db import models

from hi.apps.entity.models import Entity

from .enums import ControllerType, ControlledAreaType


class Controller( models.Model ):
    """
    - Represents an action that can be taken.
    - Will control zero or more Entities
    - When controling multiple entities, it is a single action that is broadcast to all.
    - The ControllerType implies what types of entities are typically controlled.
    """
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'controllers',
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    controller_type_str = models.CharField(
        'Controller Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Controller'
        verbose_name_plural = 'Controllers'

    @property
    def controller_type(self):
        return ControllerType.from_name_safe( self.controller_type_str )

    @controller_type.setter
    def controller_type( self, controller_type : ControllerType ):
        self.controller_type_str = str(controller_type)
        return

    
class ControlledEntity(models.Model):

    controller = models.ForeignKey(
        Controller,
        related_name = 'controlled_entities',
        verbose_name = 'Controller',
        on_delete=models.CASCADE,
    )
    controlled_entity = models.ForeignKey(
        Entity,
        related_name = 'control_sources',
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



    # ????  !!! Not needed if an entity can be an Area?

    
    
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
        self.controlled_area_type_str = str(controlled_area_type)
        return

    
class ControllerHistory(models.Model):

    controller = models.ForeignKey(
        Controller,
        related_name = 'history',
        verbose_name = 'Controller',
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

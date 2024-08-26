from django.db import models

from hi.apps.entity.models import Entity, EntityState
from hi.integrations.core.models import IntegrationIdModel

from .enums import ControllerType


class Controller( IntegrationIdModel ):
    """
    - Represents an action that can be taken.
    - Will control exactly one EntityState
    """
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    entity_state = models.ForeignKey(
        EntityState,
        related_name = 'controllers',
        verbose_name = 'Entity State',
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

    
class ControlledEntity( models.Model ):
    """The Entity associated with a Controller's state is implicitly a
    "controlled" entity, but this may also be controlling (directly or
    indirectly) the state of more than one entity.

    e.g., A light switch's on/off state is controlling the state of the
    switch, but also indirectly controlling the state of the light bulb.

    e.g., A sprinkler controller's on/off state for a zone is indirectly
    controlling a sprinkler valve as well as the sprinkler heads in that
    zone.
    """
    controller = models.ForeignKey(
        Controller,
        related_name = '+',
        verbose_name = 'Controller',
        on_delete=models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'controlled_by',
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    
    class Meta:
        verbose_name = 'Controlled Entity'
        verbose_name_plural = 'Controlled Entities'

    
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
    
    class Meta:
        verbose_name = 'Controller History'
        verbose_name_plural = 'Controller History'

from django.db import models

from hi.apps.entity.models import EntityState
from hi.integrations.core.models import IntegrationKeyModel

from .enums import ControllerType


class Controller( IntegrationKeyModel ):
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
        on_delete = models.CASCADE,
    )
    controller_type_str = models.CharField(
        'Controller Type',
        max_length = 32,
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'Controller'
        verbose_name_plural = 'Controllers'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'integration_id', 'integration_name' ],
                name = 'controller_integration_key',
            ),
        ]

    @property
    def controller_type(self):
        return ControllerType.from_name_safe( self.controller_type_str )

    @controller_type.setter
    def controller_type( self, controller_type : ControllerType ):
        self.controller_type_str = str(controller_type)
        return

    @property
    def choices(self):
        return [ ( k, v ) for k, v in self.entity_state.value_range_dict.items() ]

        
class ControllerHistory(models.Model):

    controller = models.ForeignKey(
        Controller,
        related_name = 'history',
        verbose_name = 'Controller',
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
        verbose_name = 'Controller History'
        verbose_name_plural = 'Controller History'

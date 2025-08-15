from django.db import models

from hi.apps.entity.models import EntityState
from hi.integrations.models import IntegrationDataModel

from .enums import ControllerType


class Controller( IntegrationDataModel ):
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
    persist_history = models.BooleanField(
        'Persist History',
        default = True,
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

    def __str__(self):
        return f'{self.name} ({self.entity_state.entity_state_type}) [{self.id}] ({self.integration_id})'
        
    @property
    def controller_type(self):
        return ControllerType.from_name_safe( self.controller_type_str )

    @controller_type.setter
    def controller_type( self, controller_type : ControllerType ):
        self.controller_type_str = str(controller_type)
        return

    @property
    def choices(self):
        return self.entity_state.choices()

        
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
        db_index = True,
    )
    
    class Meta:
        verbose_name = 'Controller History'
        verbose_name_plural = 'Controller History'
        ordering = [ '-created_datetime' ]

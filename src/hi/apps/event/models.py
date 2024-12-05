from django.db import models

from hi.apps.entity.models import EntityState


class EventDefinition( models.Model ):

    name = models.CharField(
        'Name',
        max_length = 64,
    )
    severity_levels_str = models.TextField(
        'Severity Levels',
        blank = True, null = True,
    )
    event_window_secs = models.PositiveIntegerField(
        'Event Window Secs',
    )
    enabled = models.BooleanField(
        default = True,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now = True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Event Definition'
        verbose_name_plural = 'Event Definitions'


class EventClause( models.Model ):

    event_definition = models.ForeignKey(
        EventDefinition,
        related_name = 'clauses',
        verbose_name = 'Event Definition',
        on_delete = models.CASCADE,
    )
    entity_state = models.ForeignKey(
        EntityState,
        related_name = '+',
        verbose_name = 'Entity State',
        on_delete = models.CASCADE,
    )
    value = models.CharField(
        'Value',
        max_length = 255
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now = True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Event Clause'
        verbose_name_plural = 'Event Clauses'
    
        
class EventHistory( models.Model ):








    
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Event History'
        verbose_name_plural = 'Event History'

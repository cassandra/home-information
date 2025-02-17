from django.db import models

from hi.apps.alert.enums import AlarmLevel
from hi.apps.control.models import Controller
from hi.apps.entity.models import EntityState
from hi.apps.security.enums import SecurityLevel

from hi.integrations.models import IntegrationKeyModel

from .enums import EventType


class EventDefinition( IntegrationKeyModel ):

    name = models.CharField(
        'Name',
        max_length = 64,
    )
    event_type_str = models.CharField(
        'Event Type',
        max_length = 32,
        null = False, blank = False,
    )

    # For multi-clause event definitions, the span in which all clauses
    # need to satisfied.
    #
    event_window_secs = models.PositiveIntegerField(
        'Event Window Secs',
    )

    # Rate limits how many events will be generated for this
    # EventDefinition by ensuring at least this time elapsed before a new
    # event would be generated.
    #
    dedupe_window_secs = models.PositiveIntegerField(
        'Dedupe Window Secs',
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

    @property
    def event_type(self):
        return EventType.from_name_safe( self.event_type_str )

    @event_type.setter
    def event_type( self, event_type : EventType ):
        self.event_type_str = str(event_type)
        return


class EventClause( models.Model ):

    event_definition = models.ForeignKey(
        EventDefinition,
        related_name = 'event_clauses',
        verbose_name = 'Event Definition',
        on_delete = models.CASCADE,
    )
    entity_state = models.ForeignKey(
        EntityState,
        related_name = '+',
        verbose_name = 'Item State',
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


class AlarmAction( models.Model ):

    event_definition = models.ForeignKey(
        EventDefinition,
        related_name = 'alarm_actions',
        verbose_name = 'Event Definition',
        on_delete = models.CASCADE,
    )
    security_level_str = models.CharField(
        'Security Level',
        max_length = 32,
        null = False, blank = False,
    )
    alarm_level_str = models.CharField(
        'Alarm Level',
        max_length = 32,
        null = False, blank = False,
    )

    # How long will this alarm be relevant to the user.  Alarms exist until
    # they expire or are acknowledged.  Set this to zero for ann alarm that
    # will only be dismissed by a user acknowledgement.
    #
    alarm_lifetime_secs = models.PositiveIntegerField(
        'Lifetime Secs',
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
        verbose_name = 'Alarm Actions'
        verbose_name_plural = 'Alarm Actions'

    @property
    def security_level(self):
        return SecurityLevel.from_name_safe( self.security_level_str )

    @security_level.setter
    def security_level( self, security_level : SecurityLevel ):
        self.security_level_str = str(security_level)
        return

    @property
    def alarm_level(self):
        return AlarmLevel.from_name_safe( self.alarm_level_str )

    @alarm_level.setter
    def alarm_level( self, alarm_level : AlarmLevel ):
        self.alarm_level_str = str(alarm_level)
        return

        
class ControlAction( models.Model ):

    event_definition = models.ForeignKey(
        EventDefinition,
        related_name = 'control_actions',
        verbose_name = 'Event Definition',
        on_delete = models.CASCADE,
    )
    controller = models.ForeignKey(
        Controller,
        related_name = 'control_actions',
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
        blank = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now = True,
        blank = True,
    )

    class Meta:
        verbose_name = 'Control Action'
        verbose_name_plural = 'Control Actions'

        
class EventHistory( models.Model ):

    event_definition = models.ForeignKey(
        EventDefinition,
        related_name = 'history',
        verbose_name = 'Event Definition',
        on_delete = models.CASCADE,
    )
    event_datetime = models.DateTimeField(
        'Timestamp',
        db_index = True,
    )
    
    class Meta:
        verbose_name = 'Event History'
        verbose_name_plural = 'Event History'
        ordering = [ '-event_datetime' ]

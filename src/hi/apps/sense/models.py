import json

from django.db import models

from hi.apps.entity.models import EntityState

from hi.integrations.models import IntegrationDetailsModel

from .enums import SensorType, CorrelationRole


class SensorHistoryManager(models.Manager):
    def filter_video_browse(self):
        """Return queryset filtered for video browsing - records with END
        correlation role.  We do this mostly because of the ZoneMinder
        integration behavior where the video duration time is only known on
        the end event.

        If we did not filter at all, we would be getting the start and end
        events for the same video stream and thus have duplicates
        everywhere.
        """
        return self.filter(correlation_role_str=str(CorrelationRole.END))


class Sensor( IntegrationDetailsModel ):
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
        on_delete = models.CASCADE,
    )
    sensor_type_str = models.CharField(
        'Sensor Type',
        max_length = 32,
        null = False, blank = False,
    )
    persist_history = models.BooleanField(
        'Persist History',
        default = True,
    )
    provides_video_stream = models.BooleanField(
        'Provides Video Stream',
        default = False,
    )
    
    class Meta:
        verbose_name = 'Sensor'
        verbose_name_plural = 'Sensors'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'integration_id', 'integration_name' ],
                name = 'sensor_integration_key',
            ),
        ]

    def __repr__(self):
        return f'{self.name} ({self.entity_state.entity_state_type}) [{self.id}] ({self.integration_id})'
            
    def __str__(self):
        return self.__repr__()
    
    @property
    def sensor_type(self):
        return SensorType.from_name_safe( self.sensor_type_str )

    @sensor_type.setter
    def sensor_type( self, sensor_type : SensorType ):
        self.sensor_type_str = str(sensor_type)
        return

    @property
    def css_class(self):
        return f'hi-sensor-{self.id}'

    
class SensorHistory(models.Model):

    objects = SensorHistoryManager()

    sensor = models.ForeignKey(
        Sensor,
        related_name = 'history',
        verbose_name = 'Sensor',
        on_delete = models.CASCADE,
    )
    value = models.CharField(
        'Value',
        max_length = 255
    )
    details = models.TextField(
        'Details',
        blank = True, null = True,
    )
    source_image_url = models.TextField(
        'Image URL',
        blank = True, null = True,
    )
    has_video_stream = models.BooleanField(
        'Has Video Stream',
        default = False,
    )
    correlation_role_str = models.CharField(
        'Correlation Role',
        max_length = 32,
        null = True, blank = True,
    )
    correlation_id = models.CharField(
        'Correlation ID',
        max_length = 32,
        null = True, blank = True,
    )
    response_datetime = models.DateTimeField(
        'Timestamp',
        db_index = True,
    )

    class Meta:
        verbose_name = 'Sensor History'
        verbose_name_plural = 'Sensor History'
        ordering = [ '-response_datetime' ]
        indexes = [
            models.Index( fields = [ 'sensor', '-response_datetime'] ),
        ]
        
    @property
    def detail_attrs(self):
        if self.details:
            return json.loads( self.details )
        return dict()

    @property
    def correlation_role(self) -> CorrelationRole:
        if self.correlation_role_str:
            return CorrelationRole.from_name_safe(self.correlation_role_str)
        return None

    @correlation_role.setter
    def correlation_role(self, correlation_role: CorrelationRole):
        self.correlation_role_str = str(correlation_role) if correlation_role else None
    

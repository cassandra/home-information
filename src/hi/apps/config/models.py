from django.db import models

from hi.apps.attribute.models import AttributeModel, AttributeValueHistoryModel


class Subsystem( models.Model ):

    name = models.CharField(
        'Name',
        max_length = 128,
        null = False, blank = False,
    )
    subsystem_key = models.CharField(
        'Subsystem Key',
        max_length = 32,
        null = False, blank = False,
        unique = True,
    )  
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Subsystem'
        verbose_name_plural = 'Subsystems'

    def __str__(self):
        return self.subsystem_key

    
class SubsystemAttribute( AttributeModel ):

    subsystem = models.ForeignKey(
        Subsystem,
        related_name = 'attributes',
        verbose_name = 'Subsystem',
        on_delete = models.CASCADE,
    )
    setting_key = models.CharField(
        'Setting Key',
        max_length = 255,
        null = False, blank = False,
    )  

    class Meta:
        verbose_name = 'Subsystem Attribute'
        verbose_name_plural = 'Subsystem Attributes'

    def get_upload_to(self):
        return 'settings/'
    
    def _get_history_model_class(self):
        """Return the history model class for SubsystemAttribute."""
        return SubsystemAttributeHistory


class SubsystemAttributeHistory(AttributeValueHistoryModel):
    """History tracking for SubsystemAttribute changes."""
    
    attribute = models.ForeignKey(
        SubsystemAttribute,
        related_name='history',
        verbose_name='Subsystem Attribute',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Subsystem Attribute History'
        verbose_name_plural = 'Subsystem Attribute History'
        indexes = [
            models.Index(fields=['attribute', '-changed_datetime']),
        ]

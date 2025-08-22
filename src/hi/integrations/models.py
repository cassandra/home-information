from typing import Dict

from django.db import models

from hi.apps.attribute.models import AttributeModel, AttributeValueHistoryModel

from .transient_models import IntegrationKey, IntegrationDetails
from .managers import IntegrationDetailsManager


class Integration( models.Model ):

    integration_id = models.CharField(
        'Integration Id',
        max_length = 64,
        null = False, blank = False,
        unique = True,
    )
    is_enabled = models.BooleanField(
        'Enabled?',
        default = False,
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
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'

    def __str__(self):
        return self.integration_id
   
    @property
    def attributes_by_name(self) -> Dict[ str, 'IntegrationAttribute' ]:
        return { attr.name: attr for attr in self.attributes.all() }

    @property
    def attributes_by_integration_key(self) -> Dict[ IntegrationKey, 'IntegrationAttribute' ]:
        return { attr.integration_key: attr for attr in self.attributes.all() }
    

class IntegrationAttribute( AttributeModel ):
    
    integration = models.ForeignKey(
        Integration,
        related_name = 'attributes',
        verbose_name = 'Integration',
        on_delete = models.CASCADE,
    )

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'

    def get_upload_to(self):
        return 'integration/attributes/'
    
    def _get_history_model_class(self):
        """Return the history model class for IntegrationAttribute."""
        return IntegrationAttributeHistory
        
        
class IntegrationDetailsModel( models.Model ):
    """
    For use in DB objects that need to be associated with an integration
    device, sensor, controller, attribute, etc.
    """
    objects = IntegrationDetailsManager()
    
    class Meta:
        abstract = True

    integration_id = models.CharField(
        'Integration Id',
        max_length = 32,
        null = True, blank = True,
    )
    integration_name = models.CharField(
        'Integration Name',
        max_length = 128,
        null = True, blank = True,
    )
    integration_payload = models.JSONField(
        'Integration Payload',
        default = dict,
        blank = True,
        help_text = 'Integration-specific data (e.g., HA domain, device capabilities)',
    )

    @property
    def integration_key(self) -> IntegrationKey:
        return IntegrationKey(
            integration_id = self.integration_id,
            integration_name = self.integration_name,
        )

    @integration_key.setter
    def integration_key( self, integration_key : IntegrationKey ):
        if not integration_key:
            self.integration_id = None
            self.integration_name = None
            return            
        self.integration_id = integration_key.integration_id
        self.integration_name = integration_key.integration_name
        return 

    def get_integration_details(self) -> IntegrationDetails:
        return IntegrationDetails(
            key = self.integration_key,
            payload = self.integration_payload,
        )

    def update_integration_payload(self, new_payload: dict) -> list:
        """
        Update integration payload and return list of changed fields.
        Only reports changes to existing fields (ignores new fields).
        Returns list of strings describing changes, empty if no existing values changed.
        """
        old_payload = self.integration_payload or {}
        changed_fields = []
        
        # Check for changes to existing fields only
        for key, new_value in new_payload.items():
            if key in old_payload and old_payload[key] != new_value:
                changed_fields.append(f'{key}: {old_payload[key]} -> {new_value}')
        
        # Always update payload (even if no existing fields changed)
        self.integration_payload = new_payload
        self.save()
        
        return changed_fields


class IntegrationAttributeHistory(AttributeValueHistoryModel):
    """History tracking for IntegrationAttribute changes."""
    
    attribute = models.ForeignKey(
        IntegrationAttribute,
        related_name='history',
        verbose_name='Integration Attribute',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Integration Attribute History'
        verbose_name_plural = 'Integration Attribute History'
        indexes = [
            models.Index(fields=['attribute', '-changed_datetime']),
        ]

from typing import Dict

from django.db import models

from hi.apps.attribute.models import AttributeModel

from .integration_key import IntegrationKey, IntegrationData
from .managers import IntegrationKeyManager


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
        
        
class IntegrationKeyModel( models.Model ):
    """
    For use in DB objects that need to be associated with an integration
    device, sensor, controller, attribute, etc.
    """
    objects = IntegrationKeyManager()
    
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
    integration_metadata = models.JSONField(
        'Integration Metadata',
        default = dict,
        blank = True,
        help_text = 'Integration-specific metadata (e.g., HA domain, device capabilities)',
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

    def get_integration_data(self) -> IntegrationData:
        return IntegrationData(
            key = self.integration_key,
            metadata = self.integration_metadata,
        )

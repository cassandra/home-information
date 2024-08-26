from dataclasses import dataclass
from typing import Dict

from django.db import models

from .enums import IntegrationType, PropertyValueType


class Integration( models.Model ):

    integration_type_str = models.CharField(
        'Integration Type',
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
        return f'{self.integration_type_str}'
   
    @property
    def integration_type(self):
        return IntegrationType.from_name_safe( self.integration_type_str )

    @integration_type.setter
    def integration_type( self, integration_type : IntegrationType ):
        self.integration_type_str = str(integration_type)
        return

    @property
    def property_dict(self) -> Dict[ str, 'IntegrationProperty' ] :
        property_dict = dict()
        for prop in self.properties.all():
            property_dict[prop.name] = prop
            continue
        return property_dict
    

class IntegrationProperty(models.Model):
    
    integration = models.ForeignKey(
        Integration,
        related_name = 'properties',
        verbose_name = 'Integration',
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
    )
    value = models.TextField(
        'Value',
    )
    value_type_str = models.CharField(
        'Value Type',
        max_length = 32,
        null = False, blank = False,
    )
    is_editable = models.BooleanField(
        'Editable?',
        default = True,
    )
    is_required = models.BooleanField(
        'Required?',
        default = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now=True,
        blank = True,
    )

    class Meta:
        verbose_name = 'Property'
        verbose_name_plural = 'Properties'

    @property
    def value_type(self):
        return PropertyValueType.from_name_safe( self.value_type_str )

    @value_type.setter
    def value_type( self, value_type : PropertyValueType ):
        self.value_type_str = str(value_type)
        return


@dataclass
class IntegrationId:
    """ Internal data corresponding to/from IntegrationIdModel """

    integration_type  : IntegrationType
    key   : str

    @property
    def integration_type_str(self):
        if self.integration_type:
            return str(self.integration_type)
        return None

    
class IntegrationIdModel( models.Model ):
    """
    For use in DB objects that need to be associated with an integration
    device/sensor/control.
    """
    
    class Meta:
        abstract = True

    integration_type_str = models.CharField(
        'Integration Type',
        max_length = 32,
        null = True, blank = True,
    )
    integration_key = models.CharField(
        'Integration Key',
        max_length = 128,
        null = True, blank = True,
    )

    @property
    def integration_type(self):
        return IntegrationType.from_name_safe( self.integration_type_str )

    @integration_type.setter
    def integration_type( self, integration_type : IntegrationType ):
        self.integration_type_str = str(integration_type)
        return 

    @property
    def integration_id(self):
        return IntegrationId(
            integration_type = self.integration_type,
            key = self.integration_key,
        )

    @integration_id.setter
    def integration_id( self, integration_id : IntegrationId ):
        if not integration_id:
            self.integration_type_str = None
            self.integration_key = None
            return            
        self.integration_type_str = integration_id.integration_type_str
        self.integration_key = integration_id.key
        return 
    
    
    

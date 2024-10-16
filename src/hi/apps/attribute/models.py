from django.db import models

from hi.apps.common.file_utils import generate_unique_filename

from hi.integrations.core.integration_key import IntegrationKey

from .enums import (
    AttributeValueType,
    AttributeType,
)


class AttributeModel(models.Model):

    class Meta:
        abstract = True
 
    name = models.CharField(
        'Name',
        max_length = 64,
    )
    value = models.TextField(
        'Value',
    )
    file_value = models.FileField(
        upload_to = 'attributes/',  # Subclasses override via get_upload_to()
        blank = True, null = True,
    )
    value_type_str = models.CharField(
        'Value Type',
        max_length = 32,
        null = False, blank = False,
    )
    integration_key_str = models.CharField(
        'Integration Key',
        max_length = 128,
        null = True, blank = True,
    )
    attribute_type_str = models.CharField(
        'Attribute Type',
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

    def __str__(self):
        return f'Attr: {self.name}={self.value} [{self.value_type_str}] [{self.attribute_type_str}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def value_type(self) -> AttributeValueType:
        return AttributeValueType.from_name_safe( self.value_type_str )

    @value_type.setter
    def value_type( self, value_type : AttributeValueType ):
        self.value_type_str = str(value_type)
        return

    @property
    def integration_key(self) -> IntegrationKey:
        if not self.integration_key_str:
            return None
        return IntegrationKey.from_string( self.integration_key_str )

    @integration_key.setter
    def integration_key( self, integration_key : IntegrationKey ):
        if integration_key:
            self.integration_key_str = str(integration_key)
        else:
            self.integration_key_str = None
        return

    @property
    def attribute_type(self) -> AttributeType:
        return AttributeType.from_name_safe( self.attribute_type_str )

    @attribute_type.setter
    def attribute_type( self, attribute_type : AttributeType ):
        self.attribute_type_str = str(attribute_type)
        return
    
    def get_upload_to(self):
        raise NotImplementedError('Subclasses should override this method.' )

    def save(self, *args, **kwargs):
        if self.file_value and self.file_value.name:
            self.file_value.field.upload_to = self.get_upload_to()
            self.file_value.name = generate_unique_filename( self.file_value.name )
        super().save(*args, **kwargs)
        return
    

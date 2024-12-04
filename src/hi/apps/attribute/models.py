import json
import logging

from django.core.files.storage import default_storage
from django.db import models

from hi.apps.attribute.attribute_enums import AttributeEnums
from hi.apps.common.file_utils import generate_unique_filename

from hi.integrations.core.integration_key import IntegrationKey

from .enums import (
    AttributeValueType,
    AttributeType,
)

logger = logging.getLogger(__name__)


class AttributeModel(models.Model):

    class Meta:
        abstract = True
 
    name = models.CharField(
        'Name',
        max_length = 64,
    )
    value = models.TextField(
        'Value',
        blank = True, null = True,
    )
    file_value = models.FileField(
        upload_to = 'attributes/',  # Subclasses override via get_upload_to()
        blank = True, null = True,
    )
    file_mime_type = models.CharField(
        'Mime Type',
        max_length = 128,
        null = True, blank = True,
    )
    value_type_str = models.CharField(
        'Value Type',
        max_length = 32,
        null = False, blank = False,
    )
    value_range_str = models.TextField(
        'Value Range',
        null = True, blank = True,
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

    def get_upload_to(self):
        raise NotImplementedError('Subclasses should override this method.' )

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

    def choices(self):
        # First check predefined ids
        choice_list = AttributeEnums.get_choices( self.value_range_str )
        if choice_list:
            return choice_list
        if not self.value_range_str:
            return list()
        try:
            value_range = json.loads( self.value_range_str )
            if isinstance( value_range, dict ):
                return [ ( k, v ) for k, v in value_range.items() ]
            if isinstance( value_range, list ):
                return [ ( x, x ) for x in value_range ]
        except json.JSONDecodeError:
            pass
        return dict()

    def save(self, *args, **kwargs):
        if self.file_value and self.file_value.name:
            self.file_value.field.upload_to = self.get_upload_to()
            self.file_value.name = generate_unique_filename( self.file_value.name )
        super().save(*args, **kwargs)
        return
    
    def delete( self, *args, **kwargs ):
        """ Deleting file from MEDIA_ROOT on best effort basis.  Ignore if fails. """
        
        if self.file_value:
            try:
                if default_storage.exists( self.file_value ):
                    default_storage.delete( self.file_value )
                    logger.debug( f'Deleted Attribute file: {self.file_value}' )
                else:
                    logger.warn( f'Attribute file not found: {self.file_value}' )
            except Exception as e:
                # Log the error or handle it accordingly
                logger.warn( f'Error deleting Attribute file {self.file_value}: {e}' )

        super().delete( *args, **kwargs )
        return

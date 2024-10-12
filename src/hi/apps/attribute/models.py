from django.db import models

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
    value_type_str = models.CharField(
        'Value Type',
        max_length = 32,
        null = False, blank = False,
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
    def attribute_type(self) -> AttributeType:
        return AttributeType.from_name_safe( self.attribute_type_str )

    @attribute_type.setter
    def attribute_type( self, attribute_type : AttributeType ):
        self.attribute_type_str = str(attribute_type)
        return
    

from django.db import models

from hi.apps.attribute.models import AttributeModel

from .enums import SubsystemAttributeType, SubsystemType


class Subsystem( models.Model ):

    name = models.CharField(
        'Name',
        max_length = 128,
        null = False, blank = False,
        unique = True,
    )
    subsystem_type_str = models.CharField(
        'Subsystem Type',
        max_length = 32,
        null = False, blank = False,
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
        return self.subsystem_type_str
    
    @property
    def subsystem_type(self) -> SubsystemType:
        return SubsystemType.from_name_safe( self.subsystem_type_str )

    @subsystem_type.setter
    def subsystem_type( self, subsystem_type : SubsystemType ):
        self.subsystem_type_str = str(subsystem_type)
        return

    
class SubsystemAttribute( AttributeModel ):

    subsystem = models.ForeignKey(
        Subsystem,
        related_name = 'attributes',
        verbose_name = 'Subsystem',
        on_delete = models.CASCADE,
    )
    subsystem_attribute_type_str = models.CharField(
        'Subsystem Attribute Type',
        max_length = 32,
        null = False, blank = False,
    )  

    class Meta:
        verbose_name = 'Subsystem Attribute'
        verbose_name_plural = 'Subsystem Attributes'

    def get_upload_to(self):
        return 'settings/'
        
    @property
    def subsystem_attribute_type(self):
        return SubsystemAttributeType.from_name_safe( self.subsystem_attribute_type_str )

    @subsystem_attribute_type.setter
    def subsystem_attribute_type( self, subsystem_attribute_type : SubsystemAttributeType ):
        self.subsystem_attribute_type_str = str(subsystem_attribute_type)
        return

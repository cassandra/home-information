from django.db import models

from hi.apps.location.models import Location

from .enums import (
    DeviceType,
    DeviceStateType,
    AttributeValueType,
    AttributeSourceType,
)


class Device( models.Model ):
    """
    - A physical or software artifact.
    - May have a fixed physical location or can just be part of a collection.
    - Maybe be located at a specific point or defined by an SVG path (e.g., wire runs, areas) 
    - Contains zero or more sensors
    - Contains zero or more controllers
    - May be controlled by zero or more controllers
    - It may have zero or more DeviceStates.
    - The state's actual value is always hidden.
    - A state may have zero of more sensors to report the state values.
    - Each sensor reports the value for a single state.
    - Each sensors reports state from a space of discrete or continuous values (or a blob).
    - Its 'DeviceType' determines is visual appearance.
    - An device can have zero or more staticly defined attributes (for information and configuration)
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'devices',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
        null = False, blank = False,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    device_type_str = models.CharField(
        'Device Type',
        max_length = 32,
        null = False, blank = False,
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
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'

    @property
    def device_type(self):
        return DeviceType.from_name_safe( self.device_type_str )

    @device_type.setter
    def device_type( self, device_type : DeviceType ):
        self.device_type_str = str(device_type)
        return

class DeviceState(models.Model):


    #  !!! Consider how to model an area with multiple temp sensors and multiple controllers to alter the temp.
    
    device = models.ForeignKey(
        Device,
        related_name = 'states',
        verbose_name = 'Device',
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    device_state_type_str = models.CharField(
        'Device State Type',
        max_length = 32,
        null = False, blank = False,
    )
    
    class Meta:
        verbose_name = 'DeviceState'
        verbose_name_plural = 'DeviceStates'

    @property
    def device_state_type(self):
        return DeviceStateType.from_name_safe( self.device_state_type_str )

    @device_state_type.setter
    def device_state_type( self, device_state_type : DeviceStateType ):
        self.device_state_type_str = str(device_state_type)
        return
    
    

class DevicePosition(models.Model):
    """For devices represented by an icon. This is the most common case. The
    icon and its styling determined by the DeviceType.  An Device is not
    required to have an DevicePosition.

    """
    
    device = models.OneToOneField(
        Device,
        related_name = 'position',
        verbose_name = 'Device',
        on_delete = models.CASCADE,
    )
    svg_x = models.DecimalField(
        'X',
        max_digits = 12,
        decimal_places = 6,
    )
    svg_y = models.DecimalField(
        'Y',
        max_digits = 12,
        decimal_places = 6,
    )
    svg_scale = models.DecimalField(
        'Scale',
        max_digits = 12,
        decimal_places = 6,
        default = 1.0,
    )
    svg_rotation = models.DecimalField(
        'Rotation',
        max_digits = 12,
        decimal_places = 6,
        default = 0.0,
    )

    class Meta:
        verbose_name = 'DevicePosition'
        verbose_name_plural = 'DevicePositionss'
    

class DevicePath(models.Model):
    """For devices represented by an arbitary SVG path. e.g., The path of a
    utility line, The styling of the path is determined by the DeviceType. An Device is not
    required to have an DevicePath.  

    """
    
    device = models.OneToOneField(
        Device,
        related_name = 'path',
        verbose_name = 'Device',
        on_delete = models.CASCADE,
    )
    svg_path = models.TextField(
        'Path',
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'DevicePath'
        verbose_name_plural = 'DevicePaths'

        
class Attribute(models.Model):
    """
    Information related to an device, e.g., specs, docs, notes, configs)
    """
    
    device = models.ForeignKey(
        Device,
        related_name = 'attributes',
        verbose_name = 'Device',
        on_delete=models.CASCADE,
    )
    attribute_value_type_str = models.CharField(
        'Attribute Value Type',
        max_length = 32,
        null = False, blank = False,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
    )
    value = models.CharField(
        'Value',
        max_length = 255
    )
    attribute_source_type_str = models.CharField(
        'Attribute Source Type',
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

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'

    @property
    def attribute_value_type(self):
        return AttributeValueType.from_name_safe( self.attribute_value_type_str )

    @attribute_value_type.setter
    def attribute_value_type( self, attribute_value_type : AttributeValueType ):
        self.attribute_value_type_str = str(attribute_value_type)
        return

    @property
    def attribute_source_type(self):
        return AttributeSourceType.from_name_safe( self.attribute_source_type_str )

    @attribute_source_type.setter
    def attribute_source_type( self, attribute_source_type : AttributeSourceType ):
        self.attribute_source_type_str = str(attribute_source_type)
        return
   

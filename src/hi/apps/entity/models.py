from django.db import models

from hi.apps.location.models import Location
from hi.integrations.core.enums import IntegrationType

from .enums import (
    EntityType,
    EntityStateType,
    AttributeValueType,
    AttributeType,
)


class Entity( models.Model ):
    """
    - A physical feature, device or software artifact.
    - May have a fixed physical location (or can just be part of a collection)
    - Maybe be located at a specific point or defined by an SVG path (e.g., paths for wire, pipes, etc.) 
    - It may have zero or more EntityStates.
    - The entity state values are always hidden.
    - A state may have zero of more sensors to report the state values.
    - Each sensor reports the value for a single state.
    - Each sensors reports state from a space of discrete or continuous values (or a blob).
    - A state may have zero or more controllers.
    - Each controller may control 
    - Its 'EntityType' determines is visual appearance.
    - An entity can have zero or more staticly defined attributes (for information and configuration)
    """
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    entity_type_str = models.CharField(
        'Entity Type',
        max_length = 32,
        null = False, blank = False,
    )
    integration_type_str = models.CharField(
        'Integration Type',
        max_length = 32,
        null = True, blank = True,
    )
    integration_id = models.CharField(
        'Integration Id',
        max_length = 128,
        null = True, blank = True,
    )
    
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'

    def __str__(self):
        return f'Entity[{self.id}]: {self.name} [{self.entity_type_str}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def entity_type(self):
        return EntityType.from_name_safe( self.entity_type_str )

    @entity_type.setter
    def entity_type( self, entity_type : EntityType ):
        self.entity_type_str = str(entity_type)
        return

    @property
    def integration_type(self):
        return IntegrationType.from_name_safe( self.integration_type_str )

    @integration_type.setter
    def integration_type( self, integration_type : IntegrationType ):
        self.integration_type_str = str(integration_type)
        return 
   
    def get_attribute_map(self):
        attribute_map = dict()
        for attribute in self.attributes.all():
            attribute_map[attribute.name] = attribute
            continue
        return attribute_map

        
class Attribute(models.Model):
    """
    - Information related to an entity, e.g., specs, docs, notes, configs
    - The 'attribute type' is used to help define what information the user might need to provide.
    """
    
    entity = models.ForeignKey(
        Entity,
        related_name = 'attributes',
        verbose_name = 'Entity',
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
    value = models.TextField(
        'Value',
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

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'
        indexes = [
            models.Index( fields=[ 'name', 'value' ] ),
        ]

    def __str__(self):
        return f'Attr: {self.name}={self.value} [{self.attribute_value_type_str}] [{self.attribute_type_str}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def attribute_value_type(self):
        return AttributeValueType.from_name_safe( self.attribute_value_type_str )

    @attribute_value_type.setter
    def attribute_value_type( self, attribute_value_type : AttributeValueType ):
        self.attribute_value_type_str = str(attribute_value_type)
        return

    @property
    def attribute_type(self):
        return AttributeType.from_name_safe( self.attribute_type_str )

    @attribute_type.setter
    def attribute_type( self, attribute_type : AttributeType ):
        self.attribute_type_str = str(attribute_type)
        return
    
    
class EntityState(models.Model):
    """
    - The (hidden) state of an entity that can be controlled and/or sensed.
    - The EntityType will help define the (default) name and value ranges (if not a general type)
    """
    
    entity = models.ForeignKey(
        Entity,
        related_name = 'states',
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    entity_state_type_str = models.CharField(
        'State Type',
        max_length = 32,
        null = False, blank = False,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    value_range = models.TextField(
        'Value Range',
        null = False, blank = False,
    )
    units = models.CharField(
        'Units',
        max_length = 32,
        null = True, blank = True,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    
    class Meta:
        verbose_name = 'Entity State'
        verbose_name_plural = 'Entity States'

    def __str__(self):
        return f'State[{self.id}]: {self.name} [{self.entity_state_type_str}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def entity_state_type(self):
        return EntityStateType.from_name_safe( self.entity_state_type_str )

    @entity_state_type.setter
    def entity_state_type( self, entity_state_type : EntityStateType ):
        self.entity_state_type_str = str(entity_state_type)
        return
    
    
class EntityPosition(models.Model):
    """
    - For entities represented by an SVG icon.
    - This is the most common case.
    - The icon and its styling determined by the EntityType. 
    - An Entity is not required to have an EntityPosition.
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'positions',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
        null = False, blank = False,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'positions',
        verbose_name = 'Entity',
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
        verbose_name = 'Entity Position'
        verbose_name_plural = 'Entity Positions'
        indexes = [
            models.Index( fields=[ 'location', 'entity' ] ),
        ]
        

class EntityPath(models.Model):
    """
    - For entities represented by an arbitary SVG path. e.g., The path of a utility line, 
    - The styling of the path is determined by the EntityType. 
    - An Entity is not required to have an EntityPath.  
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'paths',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
        null = False, blank = False,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'paths',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
    )
    svg_path = models.TextField(
        'Path',
        null = False, blank = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Entity Path'
        verbose_name_plural = 'Entity Paths'
        indexes = [
            models.Index( fields=[ 'location', 'entity' ] ),
        ]

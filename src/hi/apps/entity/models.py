from django.db import models

from hi.apps.location.models import Location

from .enums import EntityType, EntityAttributeType


class Entity( models.Model ):
    """
    - A physical object or space.
    - May have a fixed physical location or can just be part of a collection.
    - Maybe be located at a specific point or defined by an SVG path (e.g., wire runs, areas) 
    - Contains zero or more sensors
    - Contains zero or more controllers
    - May be controlled by zero or more controllers
    - It may have zero or more states.
    - The state's actual value is always hidden.
    - A state may have zero of more sensors to report the state values.
    - Each sensor reports the value for a single state.
    - Each sensors reports state from a space of discrete or continuous values (or a blob).
    - Its 'EntityType' determines is visual appearance.
    - An entity can have zero or more staticly defined attributes (for information and configuration)
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'entities',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
        null = False, blank = False,
    )
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
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'

    @property
    def entity_type(self):
        return EntityType.from_name_safe( self.entity_type_str )

    @entity_type.setter
    def entity_type( self, entity_type : EntityType ):
        self.entity_type_str = str(entity_type)
        return
        

class EntityPosition(models.Model):
    """For entities represented by an icon. This is the most common case. The
    icon and its styling determined by the EntityType.  An Entity is not
    required to have an EntityPosition.

    """
    
    entity = models.OneToOneField(
        Entity,
        related_name = 'position',
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

    class Meta:
        verbose_name = 'EntityPosition'
        verbose_name_plural = 'EntitiePositionss'
    

class EntityPath(models.Model):
    """For entities represented by an arbitary SVG path. e.g., The path of a
    utility line, The styling of the path is determined by the EntityType. An Entity is not
    required to have an EntityPath.  

    """
    
    entity = models.OneToOneField(
        Entity,
        related_name = 'path',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
    )
    svg_path = models.TextField(
        'Path',
        null = False, blank = False,
    )

    class Meta:
        verbose_name = 'EntityPath'
        verbose_name_plural = 'EntitiePaths'

        
class EntityAttribute(models.Model):
    """
    Information related to an entity, e.g., specs, docs, notes, configs)
    """
    
    entity = models.ForeignKey(
        Entity,
        related_name = 'attributes',
        verbose_name = 'Attributes',
        on_delete=models.CASCADE,
    )
    entity_attribute_type_str = models.CharField(
        'Attribute Type',
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

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'

    @property
    def entity_attribute_type(self):
        return EntityAttributeType.from_name_safe( self.entity_attribute_type_str )

    @entity_attribute_type.setter
    def entity_attribute_type( self, entity_attribute_type : EntityAttributeType ):
        self.entity_attribute_type_str = str(entity_attribute_type)
        return
   

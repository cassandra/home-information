from django.db import models

from hi.apps.location.models import Location

from .enums import EntityType, EntityAttributeType


class Entity( models.Model ):

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
   

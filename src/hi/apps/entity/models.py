import json
from typing import Dict

from django.db import models

from hi.apps.location.models import (
    Location,
    LocationItemModelMixin,
    LocationItemPositionModel,
    LocationItemPathModel,
    LocationView,
)
from hi.apps.attribute.models import AttributeModel
from hi.integrations.core.models import IntegrationKeyModel
from hi.enums import ItemType

from .enums import (
    EntityType,
    EntityStateType,
)


class Entity( IntegrationKeyModel, LocationItemModelMixin ):
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
    can_user_delete = models.BooleanField(
        'User Delete?',
        default = True,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'integration_id', 'integration_name' ],
                name = 'entity_integration_key',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.entity_type_str}) [{self.id}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def item_type(self) -> ItemType:
        return ItemType.ENTITY
    
    @property
    def entity_type(self) -> EntityType:
        return EntityType.from_name_safe( self.entity_type_str )

    @entity_type.setter
    def entity_type( self, entity_type : EntityType ):
        self.entity_type_str = str(entity_type)
        return

    def get_attribute_map(self):
        attribute_map = dict()
        for attribute in self.attributes.all():
            attribute_map[attribute.name] = attribute
            continue
        return attribute_map

        
class EntityAttribute( AttributeModel ):
    """
    - Information related to an entity, e.g., specs, docs, notes, configs
    - The 'attribute type' is used to help define what information the user might need to provide.
    """
    
    entity = models.ForeignKey(
        Entity,
        related_name = 'attributes',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
    )

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'
        indexes = [
            models.Index( fields=[ 'name', 'value' ] ),
        ]

    def get_upload_to(self):
        return 'entity/attributes/'
        
    
class EntityState( models.Model ):
    """
    - The (hidden) state of an entity that can be controlled and/or sensed.
    - The EntityType will help define the (default) name and value ranges (if not a general type)
    """
    
    entity = models.ForeignKey(
        Entity,
        related_name = 'states',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
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
    value_range_str = models.TextField(
        'Value Range',
        null = True, blank = True,
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
        return f'{self.name}[{self.id}] ({self.entity_state_type_str})'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def entity_state_type(self):
        return EntityStateType.from_name_safe( self.entity_state_type_str )

    @entity_state_type.setter
    def entity_state_type( self, entity_state_type : EntityStateType ):
        self.entity_state_type_str = str(entity_state_type)
        return

    @property
    def css_class(self):
        return f'hi-entity-state-{self.id}'

    @property
    def value_range_dict(self):
        try:
            value_range = json.loads( self.value_range_str )
            if isinstance( value_range, dict ):
                return value_range
            if isinstance( value_range, list ):
                return { x: x for x in value_range }
        except json.JSONDecodeError:
            pass
        return dict()

    @value_range_dict.setter
    def value_range_dict( self, value_dict : Dict[ str, str ] ):
        self.value_range_str = json.dumps( value_dict )
        return

    def choices(self):
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


class EntityStateDelegation(models.Model):
    """An EntityState associated with a Sensor or Controller is often serving
    representing the state of some other entity. In those cases, the entity
    containing the sensors/controllers is really just a proxy for some
    other entity's (hidden) state.  If we want to explicitly represent that
    relationship between two entities, we can define a delegation where some
    other entity becomes the "delegate" and the original entity containing the
    sensor/controller being the "principal".

        e.g., An open/close switch entity with an open/close sensor is
        directly sensing the state of the switch in the device, but it is
        indirectly trying to sense the state of a door or window. Thus, the
        door open/close "state" is being proxied by the open/close sensor's
        swith.  The open/close swith device is the principal entity while
        the door/window is the delegate entity.

        e.g., A sprinkler controller valve is directly sensing and controlling
        whether it is on or off, but also serves as a proxy for all the
        sprinkler heads connected to it.

        e.g., A temperature sensor's internal temperature states is really just
        a proxy for a area (and a Area is also an Entity).

        e.g., A motion detectors's internal "movement" state about reflected
        infrared signals is just a proxy for movement associated with a Area.

    This delegation relationship between an Entities can either be
    one-to-many or many-to-one.
    
        e.g., A thermostat may be aggregating the readings from multiple
        remote sensors so that the internal temperature state of the
        thermostat is a proxy for all the remote sensor states.

    The purpose of representing the delegation relationships is to allow
    visually changing the display of an Entity based on the sensors
    that are serving as a proxy for it.  It also allows clicks/taps on the delegate
    entity to be associated with the sensors or controllers that are proxying 
    for it.  

        e.g., A common case is for defining "Area" entities and visually
        displaying them so that they can change colors based on movement
        sensors that proxy for the area and showing the video stream for
        the camera entity proxying for the area.

    """
    
    entity_state = models.ForeignKey(
        EntityState,
        related_name = 'entity_state_delegations',
        verbose_name = 'Entity State',
        on_delete = models.CASCADE,
    )
    delegate_entity = models.ForeignKey(
        Entity,
        related_name = 'entity_state_delegations',
        verbose_name = 'Deleage Entity',
        on_delete = models.CASCADE,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Entity State Delegation'
        verbose_name_plural = 'Entity State Delegations'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'delegate_entity', 'entity_state' ],
                name = 'entity_state_delegation_uniqueness',
            ),
        ]
    
    
class EntityPosition( LocationItemPositionModel ):
    """
    - For entities represented by an SVG icon.
    - This is the most common case.
    - The icon and its styling determined by the EntityType. 
    - An Entity is not required to have an EntityPosition.
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'entity_positions',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'positions',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
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
        constraints = [
            models.UniqueConstraint(
                fields = [ 'location', 'entity' ],
                name = 'entity_position_location_entity',
            ),
        ]
            
    @property
    def location_item(self) -> LocationItemModelMixin:
        return self.entity

    
class EntityPath( LocationItemPathModel ):
    """
    - For entities represented by an arbitary SVG path. e.g., The path of a utility line, 
    - The styling of the path is determined by the EntityType. 
    - An Entity is not required to have an EntityPath.  
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'entity_paths',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'paths',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
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
        verbose_name = 'Entity Path'
        verbose_name_plural = 'Entity Paths'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'location', 'entity' ],
                name = 'entity_path_location_entity', ),
        ]
            
    @property
    def location_item(self) -> LocationItemModelMixin:
        return self.entity

    
class EntityView(models.Model):

    entity = models.ForeignKey(
        Entity,
        related_name = 'entity_views',
        verbose_name = 'Entity',
        on_delete = models.CASCADE,
    )
    location_view = models.ForeignKey(
        LocationView,
        related_name = 'entity_views',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Entity View'
        verbose_name_plural = 'Entity Views'

        constraints = [
            models.UniqueConstraint(
                fields = [ 'entity', 'location_view' ],
                name = 'entity_view_entity_location_view', ),
        ]


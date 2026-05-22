import json
from typing import Dict, List, Tuple

from django.db import models

from hi.apps.location.models import (
    Location,
    LocationItemModelMixin,
    LocationItemPositionModel,
    LocationItemPathModel,
    LocationView,
)
from hi.apps.attribute.models import AttributeModel, SoftDeleteAttributeModel, AttributeValueHistoryModel
from hi.apps.common.utils import get_humanized_name, strip_parent_name_prefix
from hi.integrations.models import IntegrationDetailsModel
from hi.enums import ItemType

from .enums import (
    EntityType,
    EntityStateRole,
    EntityStateType,
)
from .managers import EntityModelManager


class Entity( IntegrationDetailsModel, LocationItemModelMixin ):
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
    allow_internal_attributes = models.BooleanField(
        'Allow Internal Attributes?',
        default = True,
    )
    has_video_stream = models.BooleanField(
        'Has Video Stream',
        default = False,
    )
    has_video_snapshot = models.BooleanField(
        'Has Video Snapshot',
        default = False,
        help_text = (
            'Whether the source integration can provide a still image of '
            'this entity (e.g., HA camera entity_picture, ZM nph-zms '
            'mode=single). Orthogonal to has_video_stream: an entity may '
            'provide either, both, or neither capability.'
        ),
    )
    video_snapshot_stream_fps = models.FloatField(
        'Video Snapshot Stream FPS',
        null = True,
        blank = True,
        default = None,
        help_text = (
            'When has_video_snapshot is True, the rate at which the snapshot '
            'is suitable to be polled to approximate a live feed. None or 0 '
            'means snapshot exists but is not suitable for synthetic streaming.'
        ),
    )
    is_disabled = models.BooleanField(
        'Disabled?',
        default = False,
        help_text = (
            'When True, capabilities the entity would normally provide are '
            'suppressed. Used by the integration disconnect path and any '
            'future user-initiated "disable" UX.'
        ),
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    objects = EntityModelManager()

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

    @property
    def has_native_video_stream(self) -> bool:
        """Explicit-name alias for ``has_video_stream`` for the rare
        native-vs-synthetic disambiguation case. Most callers want
        ``has_live_feed`` instead."""
        return self.has_video_stream

    @property
    def has_streamable_snapshot(self) -> bool:
        """Snapshot exists and is suitable to be polled fast enough to
        approximate a live feed."""
        return self.has_video_snapshot and (self.video_snapshot_stream_fps or 0) > 0

    @property
    def has_live_feed(self) -> bool:
        """A *moving* visual is available: native stream OR a snapshot
        that can be polled. Use this on surfaces that imply motion
        (auto-view trigger, "LIVE" indicators, video-pane "live mode")."""
        return self.has_native_video_stream or self.has_streamable_snapshot

    @property
    def has_live_view(self) -> bool:
        """*Any* current visual exists, moving or static. Use this on
        surfaces that just want to show the camera (side panel buttons,
        state panels, dispatch routing)."""
        return self.has_native_video_stream or self.has_video_snapshot

    def get_attribute_map(self):
        attribute_map = dict()
        for attribute in self.attributes.all():
            attribute_map[attribute.name] = attribute
            continue
        return attribute_map

        
class EntityAttribute( SoftDeleteAttributeModel ):
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
        ordering = ['order_id', 'id']

    def get_upload_to(self):
        return 'entity/attributes/'
    
    def _get_history_model_class(self):
        """Return the history model class for EntityAttribute."""
        return EntityAttributeHistory


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
        db_index = True,
    )
    role_str = models.CharField(
        'Role',
        max_length = 64,
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
    
    def save(self, *args, **kwargs):
        # Default the role to the EntityStateType's default when not
        # explicitly set. Catches direct ``EntityState.objects.create``
        # paths; the factory layer also sets it explicitly when callers
        # don't provide one.
        if not self.role_str and self.entity_state_type_str:
            self.role_str = str( self.entity_state_type.default_role() )
        super().save( *args, **kwargs )
        return

    @property
    def entity_state_type(self):
        return EntityStateType.from_name_safe( self.entity_state_type_str )

    @entity_state_type.setter
    def entity_state_type( self, entity_state_type : EntityStateType ):
        self.entity_state_type_str = str(entity_state_type)
        return

    @property
    def entity_state_role(self) -> EntityStateRole:
        return EntityStateRole.from_name_safe( self.role_str )

    @entity_state_role.setter
    def entity_state_role( self, entity_state_role : EntityStateRole ):
        self.role_str = str(entity_state_role)
        return

    @property
    def css_class(self):
        return f'hi-entity-state-{self.id}'

    @property
    def short_name(self):
        """Name suitable for display when the entity name is already
        visible elsewhere in the surrounding chrome."""
        return strip_parent_name_prefix( self.name, self.entity.name )

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

    def choices(self) -> List[ Tuple[str,str] ]:
        # State types whose ``entity_state_value_list`` is populated
        # (OPEN_CLOSE, SMOKE, ON_OFF, ...) carry authoritative
        # labels on their EntityStateValue members. Free-form
        # discrete sets (DISCRETE state type, e.g., HA hvac_mode /
        # fan preset) store only the value strings in
        # ``value_range_str`` and rely on the humanizer for
        # readable labels.
        type_choices = self.entity_state_type.choices()
        if type_choices:
            return type_choices
        if not self.value_range_str:
            return list()
        try:
            value_range = json.loads( self.value_range_str )
        except json.JSONDecodeError:
            return list()
        if ( isinstance( value_range, dict )
             and len( value_range ) == 2
             and 'min' in value_range
             and 'max' in value_range ):
            return list()
        if isinstance( value_range, dict ):
            stored_values = list( value_range.keys() )
        elif isinstance( value_range, list ):
            stored_values = value_range
        else:
            return list()
        return [ ( str(v), get_humanized_name( str(v) ) ) for v in stored_values ]

    def toggle_values(self) -> List[str]:
        if self.value_range_str:
            try:
                # Special case for min/max types to allow toggling extremes (e.g., dimmer switches)
                value_range = json.loads( self.value_range_str )
                if (( len(value_range) == 2 )
                    and ( 'min' in value_range )
                    and ( 'max' in value_range )):
                    return [ str(value_range['min']), str(value_range['max']) ]
                
                if isinstance( value_range, dict ):
                    return [ str(k) for k, v in value_range.items() ]
                if isinstance( value_range, list ):
                    return [ str(x) for x in value_range ]
            except json.JSONDecodeError:
                pass
        return self.entity_state_type.toggle_values()
    
    def to_toggle_value( self, actual_value : str ) -> str:
        # Special case for min/max types to allow toggling extremes (e.g., dimmer switches)
        if self.value_range_str:
            try:
                value_range = json.loads( self.value_range_str )
                if (( len(value_range) == 2 )
                    and ( 'min' in value_range )
                    and ( 'max' in value_range )):
                    min_value = value_range['min']
                    max_value = value_range['max']
                    if actual_value and ( float(actual_value) > float(min_value) ):
                        return str(max_value)
                    return str(min_value)
            except ( TypeError, ValueError, json.JSONDecodeError ):
                pass
        return actual_value

        
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


class EntityAttributeHistory(AttributeValueHistoryModel):
    """History tracking for EntityAttribute changes."""
    
    attribute = models.ForeignKey(
        EntityAttribute,
        related_name='history',
        verbose_name='Entity Attribute',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Entity Attribute History'
        verbose_name_plural = 'Entity Attribute History'
        indexes = [
            models.Index(fields=['attribute', '-changed_datetime']),
        ]


class ArchivedEntity( models.Model ):
    """An archived entity preserved for historical reference.
    Created by copying an Entity's identity and attributes before deletion."""

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
    original_created_datetime = models.DateTimeField(
        'Originally Created',
        null = True, blank = True,
    )
    archived_datetime = models.DateTimeField(
        'Archived',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Archived Entity'
        verbose_name_plural = 'Archived Entities'
        ordering = ['-archived_datetime']

    def __str__( self ):
        return f'{self.name} (archived {self.archived_datetime})'

    @property
    def entity_type( self ) -> EntityType:
        return EntityType.from_name_safe( self.entity_type_str )


class ArchivedEntityAttribute( AttributeModel ):
    """An archived attribute preserved from a deleted entity."""

    archived_entity = models.ForeignKey(
        ArchivedEntity,
        related_name = 'attributes',
        verbose_name = 'Archived Entity',
        on_delete = models.CASCADE,
    )

    class Meta:
        verbose_name = 'Archived Attribute'
        verbose_name_plural = 'Archived Attributes'
        ordering = ['order_id', 'id']

    def get_upload_to( self ):
        return 'archived/entity/attributes/'

    def _get_history_model_class( self ):
        return None

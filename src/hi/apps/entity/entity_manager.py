from decimal import Decimal
import logging
from threading import local
from typing import List, Sequence, Tuple

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from hi.apps.common.singleton import Singleton
from hi.apps.location.path_geometry import PathGeometry
from hi.apps.entity.edit.forms import EntityPositionForm
from hi.apps.location.models import Location, LocationView

from .entity_pairing_manager import EntityPairingManager
from .enums import (
    EntityGroupType,
    EntityTransitionType,
)
from .models import (
    Entity,
    EntityAttribute,
    EntityPath,
    EntityPosition,
    EntityState,
    EntityStateDelegation,
    EntityView,
)
from .transient_models import (
    EntityEditModeData,
    EntityViewGroup,
    EntityViewItem,
)

logger = logging.getLogger(__name__)


class EntityManager(Singleton):

    def __init_singleton__(self):
        self._change_listeners = list()
        self.reload()
        return

    def reload(self):
        self._notify_change_listeners()
        return
        
    def register_change_listener( self, callback ):
        logger.debug( f'Adding EntityManager change listener from {callback.__module__}' )
        self._change_listeners.append( callback )
        return
    
    def _notify_change_listeners(self):
        for callback in self._change_listeners:
            try:
                callback()
            except Exception as e:
                logger.exception( 'Problem calling EntityManager change callback.', e )
            continue
        return

    def get_entity_edit_mode_data( self,
                                   entity         : Entity,
                                   location_view  : LocationView,
                                   is_editing     : bool )        -> EntityEditModeData:

        entity_position_form = None
        if is_editing and location_view:
            entity_position = EntityPosition.objects.filter(
                entity = entity,
                location = location_view.location,
            ).first()
            if entity_position:
                entity_position_form = EntityPositionForm(
                    location_view.location.svg_position_bounds,
                    instance = entity_position,
                )

        entity_pairing_list = EntityPairingManager().get_entity_pairing_list( entity = entity )
        
        return EntityEditModeData(
            entity = entity,
            entity_position_form = entity_position_form,
            entity_pairing_list = entity_pairing_list,
        )

    def set_entity_path( self,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:

        with transaction.atomic():
            try:
                entity_path = EntityPath.objects.get(
                    location = location,
                    entity_id = entity_id,
                )
                entity_path.svg_path = svg_path_str
                entity_path.save()
                return entity_path

            except EntityPath.DoesNotExist:
                pass

            entity = Entity.objects.get( id = entity_id )
            return EntityPath.objects.create(
                entity = entity,
                location = location,
                svg_path = svg_path_str,
            )
            
    def create_entity_view( self, entity : Entity, location_view : LocationView ):

        with transaction.atomic():

            # Need to make sure it has some visible representation in the view if none exists.
            entity_type = entity.entity_type
            if entity_type.requires_path():
                self.add_entity_path_if_needed(
                    entity = entity,
                    location_view = location_view,
                    is_path_closed = entity_type.requires_closed_path(),
                )
            else:
                self.add_entity_position_if_needed(
                    entity = entity,
                    location_view = location_view,
                )
            try:
                entity_view = EntityView.objects.get(
                    entity = entity,
                    location_view = location_view,
                )
            except EntityView.DoesNotExist:
                entity_view = EntityView.objects.create(
                    entity = entity,
                    location_view = location_view,
                )
        return entity_view

    def remove_entity_view( self, entity : Entity, location_view : LocationView ):

        with transaction.atomic():
            entity_view = EntityView.objects.get(
                entity = entity,
                location_view = location_view,
            )
            entity_view.delete()
        return
    
    def add_entity_to_view( self, entity : Entity, location_view : LocationView ):

        with transaction.atomic():
            # Only create delegate entities the first time an entity is added to a view.
            if not entity.entity_views.all().exists():
                delegate_entity_list = EntityPairingManager().get_delegate_entities_with_defaults(
                    entity = entity,
                )
            else:
                delegate_entity_list = EntityPairingManager().get_delegate_entities(
                    entity = entity,
                )

            _ = self.create_entity_view(
                entity = entity,
                location_view = location_view,
            )
            for delegate_entity in delegate_entity_list:
                _ = self.create_entity_view(
                    entity = delegate_entity,
                    location_view = location_view,
                )
                continue
        return 
        
    def toggle_entity_in_view( self, entity : Entity, location_view : LocationView ) -> bool:

        try:
            self.remove_entity_from_view( entity = entity, location_view = location_view )
            return False
        except EntityView.DoesNotExist:
            self.add_entity_to_view( entity = entity, location_view = location_view )
            return True
        
    def remove_entity_from_view( self, entity : Entity, location_view : LocationView ):

        with transaction.atomic():
            self.remove_entity_view(
                entity = entity,
                location_view = location_view,
            )
            EntityPairingManager().remove_delegate_entities_from_view_if_needed(
                entity = entity,
                location_view = location_view,
            )
        return
    
    def add_entity_position_if_needed( self,
                                       entity : Entity,
                                       location_view : LocationView ) -> EntityPosition:
        try:
            _ = EntityPosition.objects.get(
                location = location_view.location,
                entity = entity,
            )
            return
        except EntityPosition.DoesNotExist:
            pass

        # Default display in middle of current view
        svg_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        svg_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        
        entity_position = EntityPosition.objects.create(
            entity = entity,
            location = location_view.location,
            svg_x = Decimal( svg_x ),
            svg_y = Decimal( svg_y ),
            svg_scale = Decimal( 1.0 ),
            svg_rotate = Decimal( 0.0 ),
        )
        return entity_position
    
    def add_entity_path_if_needed( self,
                                   entity          : Entity,
                                   location_view   : LocationView,
                                   is_path_closed  : bool         ) -> EntityPath:
        try:
            _ = EntityPath.objects.get(
                location = location_view.location,
                entity = entity,
            )
            return
        except EntityPath.DoesNotExist:
            pass

        # Create default path geometry using utility function
        svg_path = PathGeometry.create_default_path_string(
            location_view=location_view,
            is_path_closed=is_path_closed,
            entity_type=entity.entity_type,
        )        
        entity_path = EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = svg_path,
        )
        return entity_path

    def handle_entity_type_transition(
            self,
            entity         : Entity,
            location_view  : LocationView   = None ) -> Tuple[bool, EntityTransitionType]:
        """
        Handle transitions between EntityType icon and path representations.
        Returns (transition_occurred, transition_type)
        """
        if not location_view:
            # If no location view provided, we can't handle position/path transitions
            return False, EntityTransitionType.NO_LOCATION_VIEW
            
        # Use EntityType structural methods instead of SvgItemFactory
        entity_type = entity.entity_type
        
        # Check current state in database
        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location_view.location,
        ).first()
        entity_path = EntityPath.objects.filter(
            entity = entity,
            location = location_view.location,
        ).first()
        
        has_position = bool(entity_position)
        has_path = bool(entity_path)
        needs_position = entity_type.requires_position()
        needs_path = entity_type.requires_path()
        
        # Check if entity has both representations (from preservation strategy)
        had_both = has_position and has_path
        
        # For entities with both, we need to determine the transition type
        # based on the actual EntityType change, not just database state
        if had_both:
            # With preservation strategy, both representations exist
            # Determine transition type based on what the NEW EntityType needs
            if needs_position:
                # Transitioning to position-based type, classify as path->icon
                # since the entity had both but will now primarily use position
                pass  # Will use path_to_icon transition
            else:
                # Transitioning to path-based type, classify as icon->path  
                # since the entity had both but will now primarily use path
                pass  # Will use icon_to_path transition
                
            # Execute the appropriate transition
            with transaction.atomic():
                if needs_position:
                    return self._transition_path_to_icon(
                        entity = entity,
                        location_view = location_view,
                        entity_path = entity_path,
                    )
                else:
                    return self._transition_icon_to_path(
                        entity = entity,
                        location_view = location_view,
                        entity_position = entity_position,
                        is_path_closed = entity_type.requires_closed_path(),
                    )
        
        with transaction.atomic():
            # Handle cases where entity doesn't have both representations
            if needs_position:
                # Entity type needs position representation
                if not has_position:
                    # Need to create position (from path center if path exists)
                    if has_path:
                        return self._transition_path_to_icon(
                            entity = entity,
                            location_view = location_view,
                            entity_path = entity_path,
                        )
                    else:
                        # No existing representation, create new position
                        self.add_entity_position_if_needed(
                            entity = entity,
                            location_view = location_view,
                        )
                        return True, EntityTransitionType.CREATED_POSITION
                else:
                    # Position already exists, just a visual update
                    return True, EntityTransitionType.ICON_TO_ICON
                    
            elif needs_path:
                # Entity type needs path representation
                if not has_path:
                    # Need to create path (from position if position exists)
                    if has_position:
                        return self._transition_icon_to_path(
                            entity = entity,
                            location_view = location_view,
                            entity_position = entity_position,
                            is_path_closed = entity_type.requires_closed_path(),
                        )
                    else:
                        # No existing representation, create new path
                        self.add_entity_path_if_needed(
                            entity = entity,
                            location_view = location_view,
                            is_path_closed = entity_type.requires_closed_path(),
                        )
                        return True, EntityTransitionType.CREATED_PATH
                else:
                    # Path already exists, just a visual update
                    return True, EntityTransitionType.PATH_TO_PATH
        
        return False, EntityTransitionType.NO_TRANSITION_NEEDED

    def _transition_icon_to_path( self,
                                  entity          : Entity,
                                  location_view   : LocationView,
                                  entity_position : EntityPosition,
                                  is_path_closed  : bool          ) -> Tuple[bool, EntityTransitionType]:
        """Create or update EntityPath based on EntityPosition location, preserving both"""
        
        # Get center point of the icon for path placement
        center_x = float(entity_position.svg_x)
        center_y = float(entity_position.svg_y)
        
        # Create path centered at icon position with larger size for better UX
        svg_path = PathGeometry.create_default_path_string(
            location_view=location_view,
            is_path_closed=is_path_closed,
            center_x=center_x,
            center_y=center_y,
            entity_type=entity.entity_type,
            radius_multiplier=2.0,  # Double size for better control point visibility
        )
        
        # Preserve EntityPosition and create/update EntityPath
        # This allows easy reversion when users change their mind
        entity_path, created = EntityPath.objects.get_or_create(
            entity = entity,
            location = location_view.location,
            defaults = {'svg_path': svg_path}
        )
        
        if not created:
            # EntityPath already exists - preserve existing geometry
            pass  # Keep existing path geometry
        
        return True, EntityTransitionType.ICON_TO_PATH

    def _transition_path_to_icon( self,
                                  entity        : Entity,
                                  location_view : LocationView,
                                  entity_path   : EntityPath    ) -> Tuple[bool, EntityTransitionType]:
        """Create or update EntityPosition based on EntityPath center, preserving both"""
        
        # Calculate geometric center of the path
        center_x, center_y = self._calculate_path_center(entity_path.svg_path)
        
        # If calculation fails, use location view center
        if center_x is None or center_y is None:
            center_x = location_view.svg_view_box.x + (location_view.svg_view_box.width / 2.0)
            center_y = location_view.svg_view_box.y + (location_view.svg_view_box.height / 2.0)
        
        # Preserve EntityPath and create/update EntityPosition
        # This allows easy reversion when users change their mind
        entity_position, created = EntityPosition.objects.get_or_create(
            entity = entity,
            location = location_view.location,
            defaults = {
                'svg_x': Decimal(center_x),
                'svg_y': Decimal(center_y),
                'svg_scale': Decimal(1.0),
                'svg_rotate': Decimal(0.0),
            }
        )
        
        if not created:
            # EntityPosition already exists - preserve existing position
            pass  # Keep existing position
        
        return True, EntityTransitionType.PATH_TO_ICON

    def _calculate_path_center( self, svg_path : str ) -> Tuple[float, float]:
        """Calculate the geometric center of an SVG path"""
        try:
            # Simple path center calculation - find all coordinate pairs and average them
            import re
            
            # Extract all numbers from the path (x,y coordinates)
            numbers = re.findall(r'[-+]?(?:\d*\.\d+|\d+)', svg_path)
            if len(numbers) < 4:  # Need at least 2 points (4 numbers)
                return None, None
                
            coords = [float(n) for n in numbers]
            
            # Group into x,y pairs
            x_coords = [coords[i] for i in range(0, len(coords), 2)]
            y_coords = [coords[i] for i in range(1, len(coords), 2)]
            
            if not x_coords or not y_coords:
                return None, None
                
            # Return the average of all points
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)
            
            return center_x, center_y
            
        except (ValueError, IndexError, ZeroDivisionError):
            return None, None

    def create_location_entity_view_group_list( self, location_view : LocationView ) -> List[EntityViewGroup]:
        existing_entities = [ x.entity
                              for x in location_view.entity_views.select_related('entity').all() ]
        all_entities = Entity.objects.all()
        return self.create_entity_view_group_list(
            existing_entities = existing_entities,
            all_entities = all_entities,
        )

    def create_entity_view_group_list( self,
                                       existing_entities  : List[ Entity ],
                                       all_entities       : Sequence[ Entity ] ) -> List[EntityViewGroup]:
        existing_entity_set = set( existing_entities )
        
        entity_view_group_dict = dict()
        for entity in all_entities:
            entity_view_item = EntityViewItem(
                entity = entity,
                exists_in_view = bool( entity in existing_entity_set ),
            )
            entity_group_type = EntityGroupType.from_entity_type( entity.entity_type )
            if entity_group_type not in entity_view_group_dict:
                entity_view_group = EntityViewGroup(
                    entity_group_type = entity_group_type,
                )
                entity_view_group_dict[entity_group_type] = entity_view_group
            entity_view_group_dict[entity_group_type].item_list.append( entity_view_item )
            continue

        for entity_group_type, entity_view_group in entity_view_group_dict.items():
            entity_view_group.item_list.sort( key = lambda item : item.entity.name )
            continue
        
        entity_view_group_list = list( entity_view_group_dict.values() )
        entity_view_group_list.sort( key = lambda item : item.entity_group_type.label )
        return entity_view_group_list
    
    def get_view_stream_entities(self) -> List[ Entity ]:
        """ Return all entities that have a video stream capability """
        # Phase 4: Use has_video_stream flag instead of VIDEO_STREAM EntityState
        return list(Entity.objects.filter(has_video_stream=True))

    
_thread_local = local()


def do_entity_manager_reload():
    logger.debug( 'Reloading EntityManager from model changes.')
    EntityManager().reload()
    _thread_local.reload_registered = False
    return


@receiver( post_save, sender = Entity )
@receiver( post_save, sender = EntityState )
@receiver( post_save, sender = EntityAttribute )
@receiver( post_save, sender = EntityStateDelegation )
@receiver( post_save, sender = EntityPosition )
@receiver( post_save, sender = EntityPath )
@receiver( post_save, sender = EntityView )
@receiver( post_delete, sender = Entity )
@receiver( post_delete, sender = EntityState )
@receiver( post_delete, sender = EntityAttribute )
@receiver( post_delete, sender = EntityStateDelegation )
@receiver( post_delete, sender = EntityPosition )
@receiver( post_delete, sender = EntityPath )
@receiver( post_delete, sender = EntityView )
def entity_manager_model_changed( sender, instance, **kwargs ):
    """
    Queue the EntityManager.reload() call to execute after the transaction
    is committed.  This prevents reloading multiple times if multiple
    models saved as part of a transaction.
    """
    if not hasattr(_thread_local, "reload_registered"):
        _thread_local.reload_registered = False

    logger.debug( 'EntityManager model change detected.')
        
    if not _thread_local.reload_registered:
        logger.debug( 'Queuing EntityManager reload on model change.')
        _thread_local.reload_registered = True
        transaction.on_commit( do_entity_manager_reload )
    
    return
        

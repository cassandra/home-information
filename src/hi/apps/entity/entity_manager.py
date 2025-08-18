from decimal import Decimal
import logging
from threading import local
from typing import List, Sequence, Tuple

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from hi.apps.common.singleton import Singleton
from hi.apps.entity.edit.forms import EntityPositionForm
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory

from .entity_pairing_manager import EntityPairingManager
from .enums import (
    EntityGroupType,
    EntityStateType,
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
    EntityDetailsData,
    EntityEditData,
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

    def get_entity_details_data( self,
                                 entity         : Entity,
                                 location_view  : LocationView,
                                 is_editing     : bool )        -> EntityDetailsData:

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
        
        entity_edit_data = EntityEditData( entity = entity )
        return EntityDetailsData(
            entity_edit_data = entity_edit_data,
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
            svg_item_type = SvgItemFactory().get_svg_item_type( entity )
            if svg_item_type.is_path:
                self.add_entity_path_if_needed(
                    entity = entity,
                    location_view = location_view,
                    is_path_closed = svg_item_type.is_path_closed,
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

        svg_path = SvgItemFactory().get_default_entity_svg_path_str(
            entity = entity,
            location_view = location_view,
            is_path_closed = is_path_closed,
        )        
        entity_path = EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = svg_path,
        )
        return entity_path

    def handle_entity_type_transition( self,
                                       entity         : Entity,
                                       location_view  : LocationView   = None ) -> Tuple[bool, str]:
        """
        Handle transitions between EntityType icon and path representations.
        Returns (transition_occurred, transition_type)
        """
        if not location_view:
            # If no location view provided, we can't handle position/path transitions
            return False, "no_location_view"
            
        svg_item_factory = SvgItemFactory()
        new_svg_item_type = svg_item_factory.get_svg_item_type( entity )
        
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
        needs_icon = new_svg_item_type.is_icon
        needs_path = new_svg_item_type.is_path
        
        with transaction.atomic():
            if has_position and needs_path:
                # icon → path transition
                return self._transition_icon_to_path(
                    entity = entity,
                    location_view = location_view,
                    entity_position = entity_position,
                    is_path_closed = new_svg_item_type.is_path_closed,
                )
                
            elif has_path and needs_icon:
                # path → icon transition
                return self._transition_path_to_icon(
                    entity = entity,
                    location_view = location_view,
                    entity_path = entity_path,
                )
                
            elif has_position and needs_icon:
                # icon → icon (no database change needed)
                return True, "icon_to_icon"
                
            elif has_path and needs_path:
                # path → path (no database change needed, just styling)
                return True, "path_to_path"
                
            elif not has_position and not has_path:
                # No existing representation, create appropriate one
                if needs_icon:
                    self.add_entity_position_if_needed(
                        entity = entity,
                        location_view = location_view,
                    )
                    return True, "created_position"
                else:
                    self.add_entity_path_if_needed(
                        entity = entity,
                        location_view = location_view,
                        is_path_closed = new_svg_item_type.is_path_closed,
                    )
                    return True, "created_path"
        
        return False, "no_transition_needed"

    def _transition_icon_to_path( self,
                                  entity          : Entity,
                                  location_view   : LocationView,
                                  entity_position : EntityPosition,
                                  is_path_closed  : bool          ) -> Tuple[bool, str]:
        """Convert EntityPosition to EntityPath, placing path at icon location"""
        
        # Get center point of the icon for path placement
        center_x = float(entity_position.svg_x)
        center_y = float(entity_position.svg_y)
        
        # Create a small path centered at the icon position
        svg_item_factory = SvgItemFactory()
        radius = svg_item_factory.NEW_PATH_RADIUS_PERCENT / 100.0
        
        if is_path_closed:
            # Create small rectangle centered at icon position
            radius_x = location_view.svg_view_box.width * radius / 4
            radius_y = location_view.svg_view_box.height * radius / 4
            
            top_left_x = center_x - radius_x
            top_left_y = center_y - radius_y
            top_right_x = center_x + radius_x
            top_right_y = center_y - radius_y
            bottom_right_x = center_x + radius_x
            bottom_right_y = center_y + radius_y
            bottom_left_x = center_x - radius_x
            bottom_left_y = center_y + radius_y
            
            svg_path = f'M {top_left_x},{top_left_y} L {top_right_x},{top_right_y} L {bottom_right_x},{bottom_right_y} L {bottom_left_x},{bottom_left_y} Z'
        else:
            # Create small line centered at icon position
            radius_x = location_view.svg_view_box.width * radius / 4
            start_x = center_x - radius_x
            start_y = center_y
            end_x = center_x + radius_x
            end_y = center_y
            
            svg_path = f'M {start_x},{start_y} L {end_x},{end_y}'
        
        # Delete EntityPosition and create EntityPath
        entity_position.delete()
        EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = svg_path,
        )
        
        return True, "icon_to_path"

    def _transition_path_to_icon( self,
                                  entity        : Entity,
                                  location_view : LocationView,
                                  entity_path   : EntityPath    ) -> Tuple[bool, str]:
        """Convert EntityPath to EntityPosition, placing icon at path center"""
        
        # Calculate geometric center of the path
        center_x, center_y = self._calculate_path_center(entity_path.svg_path)
        
        # If calculation fails, use location view center
        if center_x is None or center_y is None:
            center_x = location_view.svg_view_box.x + (location_view.svg_view_box.width / 2.0)
            center_y = location_view.svg_view_box.y + (location_view.svg_view_box.height / 2.0)
        
        # Delete EntityPath and create EntityPosition
        entity_path.delete()
        EntityPosition.objects.create(
            entity = entity,
            location = location_view.location,
            svg_x = Decimal(center_x),
            svg_y = Decimal(center_y),
            svg_scale = Decimal(1.0),
            svg_rotate = Decimal(0.0),
        )
        
        return True, "path_to_icon"

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
        """ Return all entities that have a video stream state """

        entity_state_queryset = EntityState.objects.select_related( 'entity' ).filter(
            entity_state_type_str = str(EntityStateType.VIDEO_STREAM),
        )
        return [ x.entity for x in entity_state_queryset ]

    
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
        

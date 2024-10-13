from decimal import Decimal

from django.db import transaction

from hi.apps.common.singleton import Singleton
from hi.apps.location.forms import LocationItemPositionForm
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory

from .entity_detail_data import EntityDetailData
from .enums import (
    EntityType,
)
from .models import (
    Entity,
    EntityPath,
    EntityPosition,
    EntityView,
)


class EntityManager(Singleton):

    def __init_singleton__(self):
        return

    def create_entity( self,
                       entity_type       : EntityType,
                       name              : str,
                       can_user_delete   : bool        = True,
                       integration_id    : str         = None,
                       integration_name  : str         = None  ) -> Entity:
        return Entity.objects.create(
            name = name,
            entity_type_str = str(entity_type),
            can_user_delete = can_user_delete,
            integration_id = integration_id,
            integration_name = integration_name,
        )
    
    def set_entity_path( self,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:

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
            
    def get_entity_position( self,
                             entity_id  : int,
                             location   : Location ) -> EntityPosition:
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return None
        
        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location,
        ).first()
        if entity_position:
            return entity_position
        return EntityPosition(
            entity = entity,
            location = location,
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

        svg_path = SvgItemFactory().get_default_svg_path_str(
            location_view = location_view,
            is_path_closed = is_path_closed,
        )        
        entity_path = EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = svg_path,
        )
        return entity_path
        
    def get_entity_detail_data( self,
                                entity                 : Entity,
                                current_location_view  : LocationView,
                                is_editing             : bool ) -> EntityDetailData:

        location_item_position_form = None
        if is_editing and current_location_view:
            entity_position = EntityPosition.objects.filter(
                entity = entity,
                location = current_location_view.location,
            ).first()
            if entity_position:
                location_item_position_form = LocationItemPositionForm.from_models(
                    location_item = entity_position.entity,
                    location_item_position = entity_position,
                )
        
        # TODO: Add attributes and other data
        return EntityDetailData(
            entity = entity,
            location_item_position_form = location_item_position_form,
        )


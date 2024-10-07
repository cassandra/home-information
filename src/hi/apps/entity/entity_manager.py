from decimal import Decimal

from django.db import transaction

from hi.apps.common.singleton import Singleton
from hi.integrations.core.enums import IntegrationType
from hi.apps.location.models import Location, LocationView

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

    PATH_EDIT_NEW_PATH_RADIUS_PERCENT = 5.0  # Preferrable if this matches Javascript new path sizing.
        
    def __init_singleton__(self):
        return

    def create_entity( self,
                       entity_type       : EntityType,
                       name              : str,
                       integration_type  : IntegrationType  = IntegrationType.NONE,
                       integration_key   : str              = None) -> Entity:
        return Entity.objects.create(
            name = name,
            entity_type_str = str(entity_type),
            integration_type_str = str(integration_type),
            integration_key = integration_key,
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
            if entity.entity_type.is_path:
                self.add_entity_path_if_needed(
                    entity = entity,
                    location_view = location_view,
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
    
    def add_entity_position_if_needed( self, entity : Entity, location_view : LocationView ) -> EntityPosition:
        assert not entity.entity_type.is_path

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
    
    def add_entity_path_if_needed( self, entity : Entity, location_view : LocationView ) -> EntityPath:
        assert entity.entity_type.is_path

        try:
            _ = EntityPath.objects.get(
                location = location_view.location,
                entity = entity,
            )
            return
        except EntityPath.DoesNotExist:
            pass

        # Note that this server-side creation of a new path is just one
        # place new paths can be created. During client-side path editing,
        # the Javascript code also uses logic to add new path segments.
        # These do not have to behave identical, but it is preferrable for
        # there to be some consistency.
        
        # Default display a line or rectangle in middle of current view with radius X% of viewbox
        center_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        center_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        radius_x = location_view.svg_view_box.width * ( self.PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 )
        radius_y = location_view.svg_view_box.height * ( self.PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 )

        if entity.entity_type.is_path_closed:
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
            start_x = center_x - radius_x
            start_y = center_y
            end_x = start_x + radius_x
            end_y = start_y
            svg_path = f'M {start_x},{start_y} L {end_x},{end_y}'
        
        entity_path = EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = svg_path,
        )
        return entity_path
        
    

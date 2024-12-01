from decimal import Decimal
from typing import List, Set

from django.db import transaction

from hi.apps.common.singleton import Singleton
from hi.apps.entity.edit.forms import EntityPositionForm
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.sense.sensor_history_manager import SensorHistoryManager
from hi.apps.sense.transient_models import EntityStateHistoryData

from .delegation_manager import DelegationManager
from .enums import (
    EntityType,
)
from .models import (
    Entity,
    EntityPath,
    EntityPosition,
    EntityStateDelegation,
    EntityView,
)
from .transient_models import (
    EntityDetailsData,
    EntityEditData,
    EntityViewGroup,
    EntityViewItem,
)


class EntityManager(Singleton):

    def __init_singleton__(self):
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
                entity_position_form = EntityPositionForm( instance = entity_position )

        principal_entity_list = self.get_principal_entity_list( entity = entity )
        
        entity_edit_data = EntityEditData( entity = entity )
        return EntityDetailsData(
            entity_edit_data = entity_edit_data,
            entity_position_form = entity_position_form,
            principal_entity_list = principal_entity_list,
        )

    def get_principal_entity_list( self, entity : Entity ) -> List[ Entity ]:
        entity_state_delegation_list = list(
            entity.entity_state_delegations.select_related('entity_state', 'entity_state__entity').all()
        )
        principal_state_list = [ x.entity_state for x in entity_state_delegation_list ]
        return list({ x.entity for x in principal_state_list })  # de-dupe
        
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
                delegate_entity_list = DelegationManager().get_delegate_entities_with_defaults(
                    entity = entity,
                )
            else:
                delegate_entity_list = DelegationManager().get_delegate_entities(
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

            DelegationManager().remove_delegate_entities_from_view_if_needed(
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

    def create_location_entity_view_group_list( self, location_view : LocationView ) -> List[EntityViewGroup]:
        existing_entities = [ x.entity
                              for x in location_view.entity_views.select_related('entity').all() ]
        return self.create_entity_view_group_list(
            existing_entities = existing_entities,
            exclude_delegates = False,
        )
    
    def create_principal_entity_view_group_list( self, entity : Entity ) -> List[EntityViewGroup]:
        existing_entities = self.get_principal_entity_list( entity = entity )
        return self.create_entity_view_group_list(
            existing_entities = existing_entities,
            exclude_delegates = True,  # Do not allow delegates to delegate
        )

    def create_entity_view_group_list( self,
                                       existing_entities : List[ Entity ],
                                       exclude_delegates : bool ) -> List[EntityViewGroup]:
        existing_entity_set = set( existing_entities )
        entity_queryset = Entity.objects.all()
        
        entity_view_group_dict = dict()
        for entity in entity_queryset:
            if exclude_delegates and entity.entity_state_delegations.exists():
                continue
            entity_view_item = EntityViewItem(
                entity = entity,
                exists_in_view = bool( entity in existing_entity_set ),
            )
            
            if entity.entity_type not in entity_view_group_dict:
                entity_view_group = EntityViewGroup(
                    entity_type = entity.entity_type,
                )
                entity_view_group_dict[entity.entity_type] = entity_view_group
            entity_view_group_dict[entity.entity_type].item_list.append( entity_view_item )
            continue

        for entity_type, entity_view_group in entity_view_group_dict.items():
            entity_view_group.item_list.sort( key = lambda item : item.entity.name )
            continue
        
        entity_view_group_list = list( entity_view_group_dict.values() )
        entity_view_group_list.sort( key = lambda item : item.entity_type.label )
        return entity_view_group_list

    def adjust_principal_entities( self, entity : Entity, desired_principal_entity_ids : Set[ int ] ):

        principal_entity_list = self.get_principal_entity_list( entity = entity )
        previous_principal_entity_map = { x.id: x for x in principal_entity_list }
        previous_principal_entity_ids = set( previous_principal_entity_map.keys() )

        to_add_entity_ids = desired_principal_entity_ids - previous_principal_entity_ids
        to_delete_entity_ids = previous_principal_entity_ids - desired_principal_entity_ids

        to_add_principal_entities = list( Entity.objects.filter( id__in = list(to_add_entity_ids) ) )

        with transaction.atomic():
            for add_principal_entity in to_add_principal_entities:
                for entity_state in add_principal_entity.states.all():
                    EntityStateDelegation.objects.create(
                        entity_state = entity_state,
                        delegate_entity = entity,
                    )
                    continue
                continue

            delegation_queryset = entity.entity_state_delegations.select_related(
                'entity_state',
                'entity_state__entity' ).all()
            for delegation in delegation_queryset:
                if delegation.entity_state.entity.id in to_delete_entity_ids:
                    delegation.delete()
                continue
        return
    

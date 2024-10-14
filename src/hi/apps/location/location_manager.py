from decimal import Decimal
import os
from typing import List

from django.core.files.storage import default_storage, FileSystemStorage
from django.db import transaction

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import (
    Collection,
    CollectionView,
)
from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_file_form import SvgFileForm
from hi.apps.common.svg_models import SvgViewBox
from hi.apps.entity.delegation_manager import DelegationManager
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import (
    Entity,
    EntityView,
)
from hi.apps.location.edit.forms import (
    LocationAttributeFormset,
    LocationEditForm,
    LocationSvgFileForm,
    LocationViewEditForm,
)

from .enums import LocationViewType
from .location_detail_data import LocationDetailData
from .location_view_data import LocationViewData
from .models import (
    Location,
    LocationView,
)
from .transient_models import (
    EntityViewGroup,
    EntityViewItem,
    CollectionViewItem,
    CollectionViewGroup,
)


class LocationManager(Singleton):

    INITIAL_LOCATION_VIEW_NAME = 'All'

    def __init_singleton__(self):
        return

    def create_location( self,
                         name                   : str,
                         svg_fragment_filename  : str,
                         svg_fragment_content   : str,
                         svg_viewbox            : SvgViewBox ) -> LocationView:

        last_location = Location.objects.all().order_by( '-order_id' ).first()
        if last_location:
            order_id = last_location.order_id + 1
        else:
            order_id = 0
            
        self._ensure_directory_exists( svg_fragment_filename )
        with default_storage.open( svg_fragment_filename, 'w') as destination:
            destination.write( svg_fragment_content )
        
        with transaction.atomic():
            location = Location.objects.create(
                name = name,
                svg_fragment_filename= svg_fragment_filename,
                svg_view_box_str = str( svg_viewbox ),
                order_id = order_id,
            )
            
            _ = self.create_location_view(
                location = location,
                name = self.INITIAL_LOCATION_VIEW_NAME,
            )
            
        return location
    
    def _ensure_directory_exists( self, filepath ):
        if isinstance( default_storage, FileSystemStorage ):
            directory = os.path.dirname( default_storage.path( filepath ))

            if not os.path.exists( directory ):
                os.makedirs( directory, exist_ok = True )
        return
    
    def get_location_detail_data( self, location_view : LocationView ) -> LocationDetailData:
        # TODO: Add attributes and other data
        return LocationDetailData(
            location = location_view.location,
            location_edit_form = LocationEditForm( instance = location_view.location ),
            location_attribute_formset = LocationAttributeFormset(
                instance = location_view.location,
                form_kwargs = {
                    'is_editable': True,
                },
            ),
            location_svg_file_form = LocationSvgFileForm( ),
            location_view = location_view,
            location_view_edit_form = LocationViewEditForm(  instance = location_view ),
        )
    
    def create_location_view( self,
                              location  : Location,
                              name      : str          ) -> LocationView:

        last_location_view = location.views.order_by( '-order_id' ).first()
        if last_location_view:
            order_id = last_location_view.order_id + 1
        else:
            order_id = 0
            
        return LocationView.objects.create(
            location = location,
            location_view_type_str = LocationViewType.default(),
            name = name,
            svg_view_box_str = str( location.svg_view_box ),
            svg_rotate = Decimal( 0.0 ),
            order_id = order_id,
        )
    
    def get_location_view_data( self, location_view : LocationView ):

        location = location_view.location
        entity_positions = list()
        entity_paths = list()
        non_displayed_entities = set()
        for entity_view in location_view.entity_views.all():
            entity = entity_view.entity
            is_visible = False
            entity_position = entity.positions.filter( location = location ).first()
            if entity_position:
                is_visible = True
                entity_positions.append( entity_position )
            entity_path = entity.paths.filter( location = location ).first()
            if entity_path:
                is_visible = True
                entity_paths.append( entity_path )
            if not is_visible:
                non_displayed_entities.add( entity )
            continue

        collection_positions = list()
        collection_paths = list()
        unpositioned_collections = list()
        for collection_view in location_view.collection_views.all():
            collection = collection_view.collection
            collection_position = collection.positions.filter( location = location ).first()
            if collection_position:
                collection_positions.append( collection_position )
            else:
                unpositioned_collections.append( collection )
            collection_path = collection.paths.filter( location = location ).first()
            if collection_path:
                collection_paths.append( collection_path )
            continue

        # These are used for reporting entities that might otherwise be
        # invisible to the user.  (not displayed on SVG and nor part of any
        # viewable collection).
        #
        orphan_entities = set()
        for entity in non_displayed_entities:
            if not entity.collections.exists():
                orphan_entities.add( entity )
            continue

        # These become bottom buttons, which can be ordered
        unpositioned_collections.sort( key = lambda item : item.order_id )

        return LocationViewData(
            location_view = location_view,
            entity_positions = entity_positions,
            entity_paths = entity_paths,
            collection_positions = collection_positions,
            collection_paths = collection_paths,
            unpositioned_collections = unpositioned_collections,
            orphan_entities = orphan_entities,
        )

    def create_entity_view_group_list( self, location_view : LocationView ) -> List[EntityViewGroup]:

        entity_queryset = Entity.objects.all()
        
        entity_view_group_dict = dict()
        for entity in entity_queryset:
        
            exists_in_view = False
            for entity_view in entity.entity_views.all():
                if entity_view.location_view == location_view:
                    exists_in_view = True
                    break
                continue

            entity_view_item = EntityViewItem(
                entity = entity,
                exists_in_view = exists_in_view,
            )
            
            if entity.entity_type not in entity_view_group_dict:
                entity_view_group = EntityViewGroup(
                    location_view = location_view,
                    entity_type = entity.entity_type,
                )
                entity_view_group_dict[entity.entity_type] = entity_view_group
            entity_view_group_dict[entity.entity_type].item_list.append( entity_view_item )
            continue

        entity_view_group_list = list( entity_view_group_dict.values() )
        entity_view_group_list.sort( key = lambda item : item.entity_type.label )
        return entity_view_group_list

    def create_collection_view_group( self, location_view : LocationView ) -> CollectionViewGroup:

        collection_queryset = Collection.objects.all()
        
        collection_view_group = CollectionViewGroup(
            location_view = location_view,
        )
        for collection in collection_queryset:
        
            exists_in_view = False
            for collection_view in collection.collection_views.all():
                if collection_view.location_view == location_view:
                    exists_in_view = True
                    break
                continue

            collection_view_item = CollectionViewItem(
                collection = collection,
                exists_in_view = exists_in_view,
            )
            collection_view_group.item_list.append( collection_view_item )
            continue

        collection_view_group.item_list.sort( key = lambda item : item.collection.name )
        return collection_view_group

    def toggle_entity_in_view( self, entity : Entity, location_view : LocationView ) -> bool:

        try:
            self.remove_entity_from_view( entity = entity, location_view = location_view )
            return False
        except EntityView.DoesNotExist:
            self.add_entity_to_view( entity = entity, location_view = location_view )
            return True
        
    def remove_entity_from_view( self, entity : Entity, location_view : LocationView ):

        with transaction.atomic():
            EntityManager().remove_entity_view(
                entity = entity,
                location_view = location_view,
            )

            DelegationManager().remove_delegate_entities_from_view_if_needed(
                entity = entity,
                location_view = location_view,
            )
            
        return
    
    def add_entity_to_view_by_id( self, entity : Entity, location_view_id : int ):
        location_view = LocationView.objects.get( id = location_view_id )
        self.add_entity_to_view( entity = entity, location_view = location_view )
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

            _ = EntityManager().create_entity_view(
                entity = entity,
                location_view = location_view,
            )
                            
            for delegate_entity in delegate_entity_list:
                _ = EntityManager().create_entity_view(
                    entity = delegate_entity,
                    location_view = location_view,
                )
                continue
            
        return 
        
    def toggle_collection_in_view( self,
                                   collection              : Collection,
                                   location_view           : LocationView ) -> bool:

        try:
            with transaction.atomic():
                CollectionManager().remove_collection_view(
                    collection = collection,
                    location_view = location_view,
                )
            return False
            
        except CollectionView.DoesNotExist:
            with transaction.atomic():
                _ = CollectionManager().create_collection_view(
                    collection = collection,
                    location_view = location_view,
                )
            return True
        
    def set_location_view_order( self, location_view_id_list  : List[int] ):

        item_id_to_order_id = {
            item_id: order_id for order_id, item_id in enumerate( location_view_id_list )
        }

        location_view_queryset = LocationView.objects.filter( id__in = location_view_id_list )
        with transaction.atomic():
            for location_view in location_view_queryset:
                location_view.order_id = item_id_to_order_id.get( location_view.id )
                location_view.save()
                continue
        return
    
    

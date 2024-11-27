from decimal import Decimal
import os
from typing import List

from django.core.files.storage import default_storage, FileSystemStorage
from django.db import transaction
from django.http import HttpRequest

from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_models import SvgViewBox
from hi.apps.monitor.status_display_helper import StatusDisplayLocationHelper

from .enums import LocationViewType
from .location_view_data import LocationViewData
from .models import (
    Location,
    LocationView,
)


class LocationManager(Singleton):

    INITIAL_LOCATION_VIEW_NAME = 'All'

    def __init_singleton__(self):
        return

    def get_location( self, request : HttpRequest, location_id : int ) -> Location:
        """
        This should always be used to fetch from the database and never using
        the "objects" query interface. The view_parameters loads the
        current default Location, so any out-of-band loading risks the
        cached view_parameters version to be different from the one
        loaded. Since so much of the app features revolve around the
        current location, not having the default update can result in hard
        to detect issues.
        """
        current_location = request.view_parameters.location
        if current_location and ( current_location.id == int(location_id) ):
            return current_location
        return Location.objects.get( id = location_id )

    def get_default_location( self, request : HttpRequest ) -> Location:
        current_location = request.view_parameters.location
        if current_location:
            return current_location
        location = Location.objects.order_by( 'order_id' ).first()
        if location:
            return location
        raise Location.DoesNotExist()
    
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
    
    def update_location_svg( self,
                             location               : Location,
                             svg_fragment_filename  : str,
                             svg_fragment_content   : str,
                             svg_viewbox            : SvgViewBox ) -> LocationView:

        self._ensure_directory_exists( svg_fragment_filename )
        with default_storage.open( svg_fragment_filename, 'w') as destination:
            destination.write( svg_fragment_content )
        
        location.svg_fragment_filename = svg_fragment_filename
        location.svg_view_box_str = str( svg_viewbox )
        location.save()
        
        return
    
    def _ensure_directory_exists( self, filepath ):
        if isinstance( default_storage, FileSystemStorage ):
            directory = os.path.dirname( default_storage.path( filepath ))

            if not os.path.exists( directory ):
                os.makedirs( directory, exist_ok = True )
        return
    
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
            location_view_type_str = str(LocationViewType.default()),
            name = name,
            svg_view_box_str = str( location.svg_view_box ),
            svg_rotate = Decimal( 0.0 ),
            order_id = order_id,
        )
    
    def get_location_view( self, request : HttpRequest, location_view_id : int ) -> LocationView:
        """
        This should always be used to fetch from the database and never using
        the "objects" query interface.  The view_parameters loads the
        current default LocationView, so any out-of-band loading risks the
        cached view_parameters version to be different from the one
        loaded. Since so much of the app features revolve around the
        current location view, not having the default update can result in
        hard to detect issues.
        """
        current_location_view = request.view_parameters.location_view
        if current_location_view and ( current_location_view.id == int(location_view_id) ):
            return current_location_view
        return LocationView.objects.select_related('location').get( id = location_view_id )
        
    def get_default_location_view( self, request : HttpRequest ) -> LocationView:
        current_location_view = request.view_parameters.location_view
        if current_location_view:
            return current_location_view

        location = self.get_default_location( request = request )
        if not location:
            raise LocationView.DoesNotExist()
                
        location_view = location.views.order_by( 'order_id' ).first()
        if not location_view:
            raise LocationView.DoesNotExist()

        return location_view
    
    def get_location_view_data( self,
                                location_view                : LocationView,
                                include_status_display_data  : bool ):

        location = location_view.location
        entity_positions = list()
        entity_paths = list()
        displayed_entities = set()
        non_displayed_entities = set()
        for entity_view in location_view.entity_views.select_related('entity').all():
            entity = entity_view.entity
            is_visible = False
            entity_position = entity.positions.filter( location = location ).first()
            if entity_position:
                is_visible = True
                entity_positions.append( entity_position )
                displayed_entities.add( entity )
            entity_path = entity.paths.filter( location = location ).first()
            if entity_path:
                is_visible = True
                entity_paths.append( entity_path )
                displayed_entities.add( entity )
            if not is_visible:
                non_displayed_entities.add( entity )
            continue

        collection_positions = list()
        collection_paths = list()
        unpositioned_collections = list()
        for collection_view in location_view.collection_views.select_related('collection').all():
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

        if include_status_display_data:
            status_display_helper = StatusDisplayLocationHelper( location_view = location_view )
            status_entity_states_map = status_display_helper.get_status_entity_states_map(
                entities = displayed_entities,
            )
        else:
            status_entity_states_map = dict()
            
        return LocationViewData(
            location_view = location_view,
            entity_positions = entity_positions,
            entity_paths = entity_paths,
            collection_positions = collection_positions,
            collection_paths = collection_paths,
            unpositioned_collections = unpositioned_collections,
            orphan_entities = orphan_entities,
            status_entity_states_map = status_entity_states_map,
        )

    def set_location_view_order( self, location_view_id_list  : List[int] ):

        item_id_to_idx = {
            item_id: order_id for order_id, item_id in enumerate( location_view_id_list )
        }

        location_view_queryset = LocationView.objects.filter( id__in = location_view_id_list )
        with transaction.atomic():
            for location_view in location_view_queryset:
                item_idx = item_id_to_idx.get( location_view.id )
                order_id = 2 * ( item_idx + 1)  # Leave gaps to make one-off insertions easier
                location_view.order_id = order_id
                location_view.save()
                continue
        return
    
    

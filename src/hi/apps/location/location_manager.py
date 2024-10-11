import os

from django.core.files.storage import default_storage, FileSystemStorage
from django.db import transaction

from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_models import SvgViewBox

from .location_detail_data import LocationDetailData
from .location_view_manager import LocationViewManager
from .models import (
    Location,
    LocationView,
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
            
            _ = LocationViewManager().create_location_view(
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
    
    def get_location_detail_data( self, location : Location ) -> LocationDetailData:
        # TODO: Add attributes and other data
        return LocationDetailData(
            location = location,
        )
    

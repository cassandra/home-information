from django.http import HttpRequest

from hi.apps.common.utils import is_ajax

from hi.enums import ViewType
from hi.exceptions import ForceSynchronousException


class HiViewMixin:

    def should_force_sync_request( self,
                                   request         : HttpRequest,
                                   next_view_type  : ViewType,
                                   next_id         : int ):
        """ Helper method for HiGridView subclases to know if they should force
        a full page refresh (turning an async request into a sync request. """
        

        # When in edit mode, a location view change needs a full
        # synchronous page load to ensure any front-end editing state and
        # views are invalidated. Else, the editing state and edit side
        # panel will be invalid for the new view.
        #
        
        if not is_ajax( request ):
            return False
        view_type_changed = bool( request.view_parameters.view_type != next_view_type )

        if ( view_type_changed
             and (( request.view_parameters.view_type == ViewType.CONFIGURATION )
                  or ( next_view_type == ViewType.CONFIGURATION ))):
            return True
        
        if next_view_type == ViewType.LOCATION_VIEW:
            view_id_changed = bool( request.view_parameters.location_view_id  != next_id )
            return bool( request.is_editing
                         and ( view_type_changed or view_id_changed ))

        elif next_view_type == ViewType.COLLECTION:
            view_id_changed = bool( request.view_parameters.collection_id != next_id )
            return bool( request.is_editing
                         and ( view_type_changed or view_id_changed ))

        return False

            
    

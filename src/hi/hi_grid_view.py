import logging
from typing import Dict
import urllib.parse

from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.template.loader import get_template
from django.urls import resolve
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax

from hi.apps.location.edit.views import LocationViewManageItemsView
from hi.apps.collection.edit.views import CollectionManageItemsView
from hi.apps.collection.models import Collection
from hi.apps.location.models import Location
from hi.apps.security.security_manager import SecurityManager

from hi.constants import DIVID
from hi.enums import ViewType
from hi.exceptions import ForceRedirectException, ForceSynchronousException
from hi.hi_async_view import HiSideView

logger = logging.getLogger(__name__)
    

class HiGridView(View):
    """
    - The Hi app 'grid' is an HTML layout that is defined in pages/hi_grid.html.
    - Most views participate in keeping that same four-pane layout.
    - There is a top and bottom control button areas with middle section of 'main' and 'side' content.
    - In normal (non-editing) view mode, the side, top and bottom panes  stays mostly indepedenent main area.
    - In editing view mode, the side panel is used to show and edit details of what is in the main area.
    - When only changing the main content, we prefer to do this asynchronously.
    - But we want to retain the context in the browser so a page refresh renders what was last displayed.
    - The browser URL will dictate what is displayed in the main content area.
    - When editing, a page URL parameter will contain a URL to the view of the side content.
    - This URL parameter for the side content also allows page refresh keeping the context of the display.
    - For this to work, the view that produces the dioe content (async) should subclass HiSideView.
    - For normal case for a View that only wants to populate the main content pane asynchronously:
      - Subclass this and provide get_main_template_name() and get_template_context()
    """
    
    HI_GRID_TEMPLATE_NAME = 'pages/hi_grid.html'    
    TOP_TEMPLATE_NAME = 'panes/top_buttons.html'    
    BOTTOM_TEMPLATE_NAME = 'panes/bottom_buttons.html'    
    SIDE_DEFAULT_TEMPLATE_NAME = 'panes/side.html'    
        
    def get_main_template_name( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')
    
    def get_template_context( self, request, *args, **kwargs ) -> Dict[ str, str ]:
        """ Can raise exceptions like BadRequest, Http404, ForceRedirectException, etc. """
        raise NotImplementedError('Subclasses must override this method.')

    def get_top_template_name( self ) -> str:
        return self.TOP_TEMPLATE_NAME
    
    def get_bottom_template_name( self ) -> str:
        return self.BOTTOM_TEMPLATE_NAME

    def get_top_template_context( self, request, *args, **kwargs ):
        if not request.view_parameters.location:
            return dict()
        location_list = list( Location.objects.all() )
        location_view_list = list( request.view_parameters.location.views.order_by( 'order_id' ))
        return {
            'location_view_list': location_view_list,
            'location_list': location_list,
        }

    def get_bottom_template_context( self, request, *args, **kwargs ):
        collection_list = list( Collection.objects.all().order_by( 'order_id' ))
        return {
            'security_status_data': SecurityManager().get_security_status_data(),
            'collection_list': collection_list,
        }

    def get(self, request, *args, **kwargs):
        if is_ajax( request ):
            return self.get_async_response( request, *args, **kwargs )
        return self.get_synchronous_response( request, *args, **kwargs )

    def get_synchronous_response( self, request, *args, **kwargs ):
        try:
            context = self.get_template_context( request, *args, **kwargs )
        except ForceRedirectException as fde:
            return redirect( fde.url )
        
        ( side_template_name,
          side_template_context ) = self.get_side_template_name_and_context( request, *args, **kwargs )

        context.update( side_template_context )
        context.update({
            'top_template_name': self.get_top_template_name(),
            'bottom_template_name': self.get_bottom_template_name(),
            'main_template_name': self.get_main_template_name(),
            'side_template_name': side_template_name,
        })
        context.update( self.get_top_template_context( request, *args, **kwargs ))
        context.update( self.get_bottom_template_context( request, *args, **kwargs ))

        return render( request, self.HI_GRID_TEMPLATE_NAME, context )
        
    def get_async_response( self, request, *args, **kwargs ):
        try:
            main_content = self.get_content( request, *args, **kwargs )
        except ForceRedirectException as fre:
            return antinode.redirect_response( url = fre.url )
        except ForceSynchronousException:
            redirect_url = request.get_full_path()
            return antinode.redirect_response( redirect_url )
        
        insert_map = { DIVID['MAIN']: main_content }
        push_url = self.get_push_url( request )

        return antinode.response(
            insert_map = insert_map,
            push_url = push_url,
        )

    def get_content( self, request, *args, **kwargs ) -> str:
        template_name = self.get_main_template_name()
        template = get_template( template_name )
        context = self.get_template_context( request, *args, **kwargs )
        return template.render( context, request = request )

    def get_push_url( self, request ):
        referrer_url = request.META.get('HTTP_REFERER', '')
        if referrer_url:
            parsed_url = urllib.parse.urlparse( referrer_url )
            query_params = urllib.parse.parse_qs( parsed_url.query )
            new_details_value = query_params.get( HiSideView.SIDE_URL_PARAM_NAME, [ None ] )[0]
        else:
            new_details_value = None

        if new_details_value:
            full_url = request.get_full_path()
            parsed_url = urllib.parse.urlparse( full_url )
            query_params = urllib.parse.parse_qs(parsed_url.query)
            query_params[HiSideView.SIDE_URL_PARAM_NAME] = [ new_details_value ]
            new_query_string = urllib.parse.urlencode(query_params, doseq=True)
            push_url = urllib.parse.urlunparse((
                '',
                '',
                parsed_url.path,
                parsed_url.params,
                new_query_string,
                parsed_url.fragment
            ))
        else:
            push_url = request.get_full_path()

        return push_url
        
    def get_side_template_name_and_context( self, request, *args, **kwargs ):
        try:
            side_url = self.get_side_url_from_request_url( request )
            side_view, side_kwargs = self.get_side_view_from_url( side_url )
            
            if not side_view:
                if request.view_parameters.is_editing:
                    if request.view_parameters.view_type.is_location_view:
                        side_view = LocationViewManageItemsView()

                    elif request.view_parameters.view_type.is_collection:
                        side_view = CollectionManageItemsView()

            if not side_view:
                return ( self.SIDE_DEFAULT_TEMPLATE_NAME, dict() )

            if not isinstance( side_view, HiSideView ):
                raise ValueError( f'Side URL has view not side class: {side_view.__class__.__name__}' )

            template_name = side_view.get_template_name()
            template_context = side_view.get_template_context( request, **side_kwargs )
            return ( template_name, template_context )
        
        except Exception as e:
            logger.exception( e )
            return ( self.SIDE_DEFAULT_TEMPLATE_NAME, dict() )

    def get_side_url_from_request_url( self, request ):
        
        full_url = request.get_full_path()
        parsed_url = urllib.parse.urlparse( full_url )
        query_params = urllib.parse.parse_qs( parsed_url.query )
        side_url = query_params.get( HiSideView.SIDE_URL_PARAM_NAME, [ None ] )[0]
        return side_url

    def get_side_view_from_url( self, url ):
        if not url:
            return ( None, dict() )
        resolved_match = resolve( url )
        view_kwargs = resolved_match.kwargs
        view_class = resolved_match.func.view_class
        view = view_class()
        return ( view, view_kwargs )
    
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
            return bool( request.view_parameters.is_editing
                         and ( view_type_changed or view_id_changed ))

        elif next_view_type == ViewType.COLLECTION:
            view_id_changed = bool( request.view_parameters.collection_id != next_id )
            return bool( request.view_parameters.is_editing
                         and ( view_type_changed or view_id_changed ))

        return False

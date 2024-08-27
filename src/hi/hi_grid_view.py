import logging
from typing import Dict

from django.http import HttpRequest
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.urls import NoReverseMatch
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax

from hi.constants import DIVID

logger = logging.getLogger(__name__)


class HiGridView(View):

    """ 
    - Helpers for views that use the main "HI Grid View" layout.
    - The HI Grid view layout has the top and bottom fixed rows (usually buttons)
      and main panel and a side panel.
    - Helps to populate areas asynchronously, but can handle sychconous requests too.
    - Good for views that populate all or just some of the tiled areas of the HIU Grid.
    - Main HI Grid layout defined in the template: pages/hi_grid.html
    """

    HI_GRID_TEMPLATE_NAME = 'pages/home.html'    
    TOP_TEMPLATE_NAME = 'panes/top_buttons.html'    
    BOTTOM_TEMPLATE_NAME = 'panes/bottom_buttons.html'    
    MAIN_TEMPLATE_NAME = 'panes/main_default.html'    
    SIDE_TEMPLATE_NAME = 'panes/side_panel.html'    

    def hi_grid_response( self,
                          request               : HttpRequest,
                          context               : Context,
                          top_template_name     : str                = None,
                          bottom_template_name  : str                = None,
                          main_template_name    : str                = None,
                          side_template_name    : str                = None,
                          push_url_name         : str                = None,
                          push_url_kwargs       : Dict[ str, str ]   = None ):
        if not context:
            context = dict()

        if not is_ajax( request ):
            # For full syncronous render, we need all content, so we fill
            # in defaults for any missing.
            if not top_template_name:
                top_template_name = self.TOP_TEMPLATE_NAME
            if not bottom_template_name:
                bottom_template_name = self.BOTTOM_TEMPLATE_NAME
            if not main_template_name:
                main_template_name = self.MAIN_TEMPLATE_NAME
            if not side_template_name:
                side_template_name = self.SIDE_TEMPLATE_NAME
            context.update({
                'top_template_name': top_template_name,
                'bottom_template_name': bottom_template_name,
                'main_template_name': main_template_name,
                'side_template_name': side_template_name,
            })

            # This list of views is needed for top buttons
            if ( request.view_parameters.location_view
                 and 'location_view_list' not in context ):
                location = request.view_parameters.location_view.location
                location_view_list = list( location.views.order_by( 'order_id' ))
                context['location_view_list'] = location_view_list
            
            return render( request, self.HI_GRID_TEMPLATE_NAME, context )

        div_id_to_template_name = {
            DIVID['TOP'] : top_template_name,
            DIVID['BOTTOM'] : bottom_template_name,
            DIVID['MAIN'] : main_template_name,
            DIVID['SIDE'] : side_template_name,
        }
        insert_map = dict()
        for div_id, template_name in div_id_to_template_name.items():
            if not template_name:
                continue
            template = get_template( template_name )
            content = template.render( context, request = request )
            insert_map[div_id] = content,
            continue

        push_url = None
        if push_url_name:
            try:
                push_url = reverse( push_url_name, kwargs = push_url_kwargs )
            except NoReverseMatch:
                logger.warning( f'No reverse url for {push_url_name}' )
                pass
        
        return antinode.response(
            insert_map = insert_map,
            push_url = push_url,
        )

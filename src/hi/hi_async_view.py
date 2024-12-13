import logging
from typing import Dict
import urllib.parse

from django.shortcuts import render
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax

from hi.constants import DIVID

logger = logging.getLogger(__name__)


class HiAsyncView( View ):
    """
    Use this when async calls always populate the same <div> Id.
    """
    
    def get_target_div_id( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def get_template_name( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def get_template_context( self, request, *args, **kwargs ) -> Dict[ str, str ]:
        """ Can raise exceptions like BadRequest, Http404, etc. """
        raise NotImplementedError('Subclasses must override this method.')

    def get_content( self, request, *args, **kwargs ) -> str:
        template_name = self.get_template_name()
        template = get_template( template_name )
        context = self.get_template_context( request, *args, **kwargs )
        return template.render( context, request = request )

    def get( self, request, *args, **kwargs ):
        div_id = self.get_target_div_id()
        content = self.get_content( request, *args, **kwargs )
        return antinode.response(
            insert_map = { div_id: content },
        )

    def post_template_context( self, request, *args, **kwargs ) -> Dict[ str, str ]:
        """ Can raise exceptions like BadRequest, Http404, etc. """
        raise NotImplementedError('Subclasses must override this method.')

    def post_content( self, request, *args, **kwargs ) -> str:
        template_name = self.get_template_name()
        template = get_template( template_name )
        context = self.post_template_context( request, *args, **kwargs )
        return template.render( context, request = request )

    def post( self, request, *args, **kwargs ):
        div_id = self.get_target_div_id()
        content = self.post_content( request, *args, **kwargs )
        return antinode.response(
            insert_map = { div_id: content },
        )
        

class HiSideView( HiAsyncView ):

    SIDE_URL_PARAM_NAME = 'details'
    
    def should_push_url( self ):
        """
        Subclasses can override this if they want full page refresh to retain
        the view in the side page.
        """
        return False
    
    def get_target_div_id( self ) -> str:
        return DIVID['SIDE']

    def get( self, request, *args, **kwargs ):
        div_id = self.get_target_div_id()
        content = self.get_content( request, *args, **kwargs )
        push_url = self.get_push_url( request )
        return antinode.response(
            insert_map = { div_id: content },
            push_url = push_url,
        )
    
    def get_push_url( self, request ):

        referrer_url_str = request.META.get('HTTP_REFERER', '')
        if not referrer_url_str:
            return None

        side_url = request.path
        referrer_url = urllib.parse.urlparse( referrer_url_str )
        referrer_query_params = urllib.parse.parse_qs( referrer_url.query )
        if self.should_push_url():
            referrer_query_params[self.SIDE_URL_PARAM_NAME] = side_url
        else:
            del referrer_query_params[self.SIDE_URL_PARAM_NAME]
            
        updated_query_string = urllib.parse.urlencode( referrer_query_params )
        return f"{referrer_url.path}?{updated_query_string}"
        
        
class HiModalView( View ):

    DEFAULT_PAGE_TEMPLATE_NAME = 'pages/main_default.html'
    
    def get_template_name( self ) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def modal_response( self, request, context, status = 200 ):
        modal_response = antinode.modal_from_template(
            request = request,
            template_name = self.get_template_name(),
            context = context,
        )
        if is_ajax( request ):
            return modal_response

        context['initial_modal_template_name'] = self.get_template_name()
        template_name = self.DEFAULT_PAGE_TEMPLATE_NAME
        return render( request,
                       template_name,
                       context,
                       status = status )

    def redirect_response( self, request, redirect_url ):
        return antinode.redirect_response( redirect_url )

    def refresh_response( self, request ):
        return antinode.refresh_response()

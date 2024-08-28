from django.http import HttpResponseRedirect
from django.urls import reverse

from hi.hi_grid_view import HiGridView
from hi.enums import EditMode


class EditStartView( HiGridView ):

    def get(self, request, *args, **kwargs):

        request.view_parameters.edit_mode = EditMode.ON
        request.view_parameters.to_session( request )
        
        context = {
        }
        return self.hi_grid_response( 
            request = request,
            context = context,
            bottom_template_name = 'edit/panes/bottom.html',
            main_template_name = 'edit/panes/main.html',
            side_template_name = 'edit/panes/side.html',
            push_url_name = 'edit_start',
            push_url_kwargs = kwargs,
        )

    
class EditEndView( HiGridView ):

    def get(self, request, *args, **kwargs):

        request.view_parameters.edit_mode = EditMode.OFF
        request.view_parameters.to_session( request )

        redirect_url = reverse( 'home' )
        return HttpResponseRedirect( redirect_url )
        

import logging

from django.core.exceptions import BadRequest
from django.http import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator

import hi.apps.common.antinode as antinode
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

from hi.decorators import edit_required
from hi.enums import ViewType
from hi.hi_async_view import HiModalView

from . import forms


logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_add.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'location_add_form': forms.LocationAddForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        
        location_add_form = forms.LocationAddForm( request.POST, request.FILES )
        if not location_add_form.is_valid():
            context = {
                'location_add_form': location_add_form,
            }
            return self.modal_response( request, context )

        try:
            location = LocationManager().create_location(
                name = location_add_form.cleaned_data.get('name'),
                svg_fragment_filename = location_add_form.cleaned_data.get('svg_fragment_filename'),
                svg_fragment_content = location_add_form.cleaned_data.get('svg_fragment_content'),
                svg_viewbox = location_add_form.cleaned_data.get('svg_viewbox'),
            )
        except ValueError as ve:
            raise BadRequest( str(ve) )

        location_view = location.views.order_by( 'order_id' ).first()
        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationSvgReplaceView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_svg_replace.html'

    def get( self, request, *args, **kwargs ):
        location_id = kwargs.get( 'location_id' )
        if not location_id:
            raise BadRequest( 'Missing location id.' )
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )
        context = {
            'location': location,
            'location_svg_file_form': forms.LocationSvgReplaceForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        location_id = kwargs.get( 'location_id' )
        if not location_id:
            raise BadRequest( 'Missing location id.' )
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )
        
        location_svg_file_form = forms.LocationSvgReplaceForm( request.POST, request.FILES )
        if not location_svg_file_form.is_valid():
            context = {
                'location': location,
                'location_svg_file_form': location_svg_file_form,
            }
            return self.modal_response( request, context )

        try:
            location = LocationManager().update_location_svg(
                location = location,
                svg_fragment_filename = location_svg_file_form.cleaned_data.get('svg_fragment_filename'),
                svg_fragment_content = location_svg_file_form.cleaned_data.get('svg_fragment_content'),
                svg_viewbox = location_svg_file_form.cleaned_data.get('svg_viewbox'),
            )
        except ValueError as ve:
            raise BadRequest( str(ve) )

        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationDeleteView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_delete.html'

    def get(self, request, *args, **kwargs):
        location_id = kwargs.get( 'location_id' )
        if not location_id:
            raise BadRequest( 'Missing location id.' )
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )

        context = {
            'location': location,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        location_id = kwargs.get( 'location_id' )
        if not location_id:
            raise BadRequest( 'Missing location id.' )
            
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )

        location.delete()

        next_location = Location.objects.all().order_by( 'order_id' ).first()
        if next_location:
            request.view_parameters.location_id = next_location.id
        else:
            request.view_parameters.location_id = None
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

        
@method_decorator( edit_required, name='dispatch' )
class LocationViewAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_view_add.html'
    
    def get( self, request, *args, **kwargs ):
        context = {
            'location_view_add_form': forms.LocationViewAddForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        location_view_add_form = forms.LocationViewAddForm( request.POST )
        if not location_view_add_form.is_valid():
            context = {
                'location_view_add_form': location_view_add_form,
            }
            return self.modal_response( request, context )

        if request.view_parameters.location_view:
            location = request.view_parameters.location_view.location
        else:
            location = Location.objects.order_by( 'order_id' ).first()
        
        try:
            location_view = LocationManager().create_location_view(
                location = location,
                name = location_view_add_form.cleaned_data.get('name'),
            )
        except ValueError as e:
            raise BadRequest( str(e) )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewDeleteView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_view_delete.html'
    
    def get(self, request, *args, **kwargs):
        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            raise BadRequest( 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            raise Http404( request )

        context = {
            'location_view': location_view,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            raise BadRequest( 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            raise Http404( request )

        location_view.delete()

        next_location_view = LocationView.objects.all().order_by( 'order_id' ).first()
        if next_location_view:
            request.view_parameters.location_view_id = next_location_view.id
        else:
            request.view_parameters.location_view_id = None
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

       

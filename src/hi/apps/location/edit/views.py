import logging

from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.models import Collection
import hi.apps.common.antinode as antinode
from hi.apps.edit.forms import NameForm
from hi.apps.entity.models import Entity
from hi.apps.location.location_view_manager import LocationViewManager
from hi.apps.location.models import LocationView
from hi.decorators import edit_required
from hi.enums import ViewType
from hi.views import bad_request_response

from hi.constants import DIVID

from .helpers import LocationEditHelpers


logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationViewAddView( View ):

    def get( self, request, *args, **kwargs ):
        context = {
            'name_form': NameForm(),
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_view_add.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        name_form = NameForm( request.POST )
        if not name_form.is_valid():
            context = {
                'name_form': name_form,
            }
            return antinode.modal_from_template(
                request = request,
                template_name = 'location/edit/modals/location_view_add.html',
                context = context,
            )

        try:
            location_view = LocationEditHelpers.create_location_view(
                request = request,
                name = name_form.cleaned_data.get('name'),
            )
        except ValueError as e:
            return bad_request_response( request, message = str(e) )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewDeleteView( View ):

    def get(self, request, *args, **kwargs):
        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            return bad_request_response( request, message = 'No current location view found.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            message = f'Location view "{location_view_id}" does not exist.'
            logger.warning( message )
            return bad_request_response( request, message = message )

        context = {
            'location_view': location_view,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_view_delete.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            return bad_request_response( request, message = 'Missing confirmation value.' )

        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            return bad_request_response( request, message = 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            message = f'Location view "{location_view_id}" does not exist.'
            logger.warning( message )
            return bad_request_response( request, message = message )

        location_view.delete()

        next_location_view = LocationView.objects.all().order_by( 'order_id' ).first()
        if next_location_view:
            request.view_parameters.location_view_id = next_location_view.id
        else:
            request.view_parameters.location_view_id = None
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewAddRemoveItemView( View ):

    def get(self, request, *args, **kwargs):

        location_view = request.view_parameters.location_view

        entity_view_group_list = LocationEditHelpers.create_entity_view_group_list(
            location_view = location_view,
        )
        collection_view_group = LocationEditHelpers.create_collection_view_group(
            location_view = location_view,
        )
        
        context = {
            'entity_view_group_list': entity_view_group_list,
            'collection_view_group': collection_view_group,
        }
        template = get_template( 'location/edit/panes/location_view_add_remove_item.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewEntityToggleView( View ):

    def post( self, request, *args, **kwargs ):

        location_view_id = kwargs.get('location_view_id')
        entity_id = kwargs.get('entity_id')

        entity = Entity.objects.get( id = entity_id )
        location_view = LocationView.objects.get( id = location_view_id )
        exists_in_view = LocationEditHelpers.toggle_entity_in_view(
            entity = entity,
            location_view = location_view,
        )
            
        context = {
            'location_view': location_view,
            'entity': entity,
            'exists_in_view': exists_in_view,
        }
        template = get_template( 'location/edit/panes/location_view_entity_toggle.html' )
        main_content = template.render( context, request = request )

        location_view_data = LocationViewManager().get_location_view_data(
            location_view = location_view,
        )
        context = {
            'location_view_data': location_view_data,
        }
        template = get_template( 'location/location_view.html' )
        location_view_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewEntityToggleCollectionView( View ):

    def post(self, request, *args, **kwargs):

        location_view_id = kwargs.get('location_view_id')
        collection_id = kwargs.get('collection_id')

        collection = Collection.objects.get( id = collection_id )
        location_view = LocationView.objects.get( id = location_view_id )
        exists_in_view = LocationEditHelpers.toggle_collection_in_view(
            collection = collection,
            location_view = location_view,
            add_position_if_needed = True,
        )
            
        context = {
            'location_view': location_view,
            'collection': collection,
            'exists_in_view': exists_in_view,
        }
        template = get_template( 'location/edit/panes/location_view_collection_toggle.html' )
        main_content = template.render( context, request = request )

        location_view_data = LocationViewManager().get_location_view_data(
            location_view = location_view,
        )
        context = {
            'location_view_data': location_view_data,
        }
        template = get_template( 'location/location_view.html' )
        location_view_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )

    

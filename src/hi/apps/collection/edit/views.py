import logging

from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.enums import CollectionType
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.edit.forms import NameForm
from hi.apps.entity.models import Entity
from hi.apps.location.forms import SvgPositionForm
from hi.decorators import edit_required
from hi.enums import ViewType
from hi.views import bad_request_response, page_not_found_response

from hi.constants import DIVID

from .helpers import CollectionEditHelpers

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class CollectionAddView( View ):

    def get( self, request, *args, **kwargs ):
        context = {
            'name_form': NameForm(),
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'collection/edit/modals/collection_add.html',
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
                template_name = 'collection/edit/modals/collection_add.html',
                context = context,
            )

        # Move to helper class
        # Extend NameForm to add type dropdown
        


        last_collection = Collection.objects.all().order_by( '-order_id' ).first()
        
        collection = Collection.objects.create(
            name = name_form.cleaned_data.get('name'),
            collection_type_str = CollectionType.default(),
            order_id = last_collection.order_id + 1,
        )
        
        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.collection_id = collection.id
        request.view_parameters.to_session( request )
 
        redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class CollectionDeleteView( View ):

    def get(self, request, *args, **kwargs):
        collection_id = request.view_parameters.collection_id
        if not collection_id:
            return bad_request_response( request, message = 'No current collection found.' )
            
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            message = f'Collection "{collection_id}" does not exist.'
            logger.warning( message )
            return bad_request_response( request, message = message )

        context = {
            'collection': collection,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'collection/edit/modals/collection_delete.html',
            context = context,
        )

    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            return bad_request_response( request, message = 'Missing confirmation value.' )

        collection_id = request.POST.get( 'collection_id' )
        if not collection_id:
            return bad_request_response( request, message = 'Missing collection id.' )
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            message = f'Collection "{collection_id}" does not exist.'
            logger.warning( message )
            return bad_request_response( request, message = message )

        collection.delete()

        next_collection = Collection.objects.all().order_by( 'order_id' ).first()
        if next_collection:
            request.view_parameters.collection_id = next_collection.id
        else:
            request.view_parameters.collection_id = None
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return redirect( redirect_url )
    
    
@method_decorator( edit_required, name='dispatch' )
class CollectionDetailsView( View ):

    def get( self, request, *args, **kwargs ):
        collection_id = kwargs.get( 'collection_id' )
        if not collection_id:
            return bad_request_response( request, message = 'Missing collection id in request.' )
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            return page_not_found_response( request, message = f'No collection with id "{collection_id}".' )

        location_view = request.view_parameters.location_view

        svg_position_form = None
        if request.view_parameters.view_type.is_location_view:
            collection_position = CollectionPosition.objects.filter(
                collection = collection,
                location = location_view.location,
            ).first()
            if collection_position:
                svg_position_form = SvgPositionForm.from_svg_position_model( collection_position )
            
        context = {
            'collection': collection,
            'svg_position_form': svg_position_form,
        }
        template = get_template( 'collection/edit/panes/collection_details.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     

    
@method_decorator( edit_required, name='dispatch' )
class CollectionAddRemoveItemView( View ):

    def get(self, request, *args, **kwargs):
        collection = request.view_parameters.collection
        
        entity_collection_group_list = CollectionEditHelpers.create_entity_collection_group_list(
            collection = collection,
        )
        
        context = {
            'entity_collection_group_list': entity_collection_group_list,
        }
        template = get_template( 'collection/edit/panes/collection_add_remove_item.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     

    
@method_decorator( edit_required, name='dispatch' )
class CollectionEntityToggleView( View ):

    def post(self, request, *args, **kwargs):

        collection_id = kwargs.get('collection_id')
        entity_id = kwargs.get('entity_id')

        entity = Entity.objects.get( id = entity_id )
        collection = Collection.objects.get( id = collection_id )
        exists_in_collection = CollectionEditHelpers.toggle_entity_in_collection(
            entity = entity,
            collection = collection,
        )
            
        context = {
            'collection': collection,
            'entity': entity,
            'exists_in_collection': exists_in_collection,
        }
        template = get_template( 'collection/edit/panes/collection_entity_toggle.html' )
        main_content = template.render( context, request = request )

        collection_data = CollectionManager().get_collection_data(
            collection = collection,
        )
        context = {
            'collection_data': collection_data,
        }
        template = get_template( 'collection/collection_view.html' )
        collection_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : collection_content,
            },
        )

    
    
    

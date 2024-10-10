import logging

from django.db import transaction
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.edit.helpers import CollectionEditHelpers
import hi.apps.common.antinode as antinode
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.location.edit.helpers import LocationEditHelpers
from hi.apps.location.forms import LocationItemPositionForm

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.views import bad_request_response, not_authorized_response, page_not_found_response

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class EntityDetailsView( View ):

    def get( self, request, *args, **kwargs ):
        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            return bad_request_response( request, message = 'Missing entity id in request.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return page_not_found_response( request, message = f'No entity with id "{entity_id}".' )

        location_view = request.view_parameters.location_view

        location_item_position_form = None
        if request.view_parameters.view_type.is_location_view:
            entity_position = EntityPosition.objects.filter(
                entity = entity,
                location = location_view.location,
            ).first()
            if entity_position:
                location_item_position_form = LocationItemPositionForm.from_svg_position_model(
                    entity_position,
                )

        context = {
            'entity': entity,
            'location_item_position_form': location_item_position_form,
        }
        template = get_template( 'entity/edit/panes/entity_details.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     

    
@method_decorator( edit_required, name='dispatch' )
class EntityAddView( View ):

    def get( self, request, *args, **kwargs ):
        context = {
            'entity_form': forms.EntityForm(),
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'entity/edit/modals/entity_add.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        entity_form = forms.EntityForm( request.POST )
        if not entity_form.is_valid():
            context = {
                'entity_form': entity_form,
            }
            return antinode.modal_from_template(
                request = request,
                template_name = 'entity/edit/modals/entity_add.html',
                context = context,
            )

        cleaned_data = entity_form.clean()
        entity_type = EntityType.from_name_safe( cleaned_data.get('entity_type') )
        name = cleaned_data.get('name')
        
        try:
            with transaction.atomic():
                entity = EntityManager().create_entity(
                    entity_type = entity_type,
                    name = name,
                )
                if ( request.view_parameters.view_type.is_location_view
                     and request.view_parameters.location_view_id ):
                    LocationEditHelpers.add_entity_to_view_by_id(
                        entity = entity,
                        location_view_id = request.view_parameters.location_view_id,
                    )
                    
                elif ( request.view_parameters.view_type.is_collection
                       and request.view_parameters.collection_id ):
                    CollectionEditHelpers.add_entity_to_collection_by_id(
                        entity = entity,
                        collection_id = request.view_parameters.collection_id,
                    )
                    
                redirect_url = reverse('home')
                return redirect( redirect_url )
    
        except ValueError as e:
            return bad_request_response( request, message = str(e) )
        

@method_decorator( edit_required, name='dispatch' )
class EntityDeleteView( View ):

    def get( self, request, *args, **kwargs ):
        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            return bad_request_response( request, message = 'Missing entity id in request.' )

        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return page_not_found_response( request )

        if not entity.can_user_delete:
            return not_authorized_response( request, message = 'This entity cannot be deleted.' )
        
        context = {
            'entity': entity,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'entity/edit/modals/entity_delete.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            return bad_request_response( request, message = 'Missing confirmation value.' )

        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            return bad_request_response( request, message = 'Missing entity id.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return page_not_found_response( request )

        if not entity.can_user_delete:
            return not_authorized_response( request, message = 'This entity cannot be deleted.' )
                
        entity.delete()

        redirect_url = reverse('home')
        return redirect( redirect_url )

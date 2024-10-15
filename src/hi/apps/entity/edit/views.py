import logging

from django.core.exceptions import BadRequest, PermissionDenied
from django.db import transaction
from django.http import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator

from hi.apps.collection.collection_manager import CollectionManager
import hi.apps.common.antinode as antinode
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager

from hi.decorators import edit_required
from hi.hi_async_view import HiModalView

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class EntityAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_add.html'
    
    def get( self, request, *args, **kwargs ):
        context = {
            'entity_form': forms.EntityForm(),
        }
        return self.modal_response( request, context )
    
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
                    name = name,
                    entity_type = entity_type,
                    can_user_delete = True,
                )
                if ( request.view_parameters.view_type.is_location_view
                     and request.view_parameters.location_view_id ):
                    LocationManager().add_entity_to_view_by_id(
                        entity = entity,
                        location_view_id = request.view_parameters.location_view_id,
                    )
                    
                elif ( request.view_parameters.view_type.is_collection
                       and request.view_parameters.collection_id ):
                    CollectionManager().add_entity_to_collection_by_id(
                        entity = entity,
                        collection_id = request.view_parameters.collection_id,
                    )
                    
            redirect_url = reverse('home')
            return self.redirect_response( request, redirect_url )
    
        except ValueError as e:
            raise BadRequest( str(e) )
        

@method_decorator( edit_required, name='dispatch' )
class EntityDeleteView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_delete.html'

    def get( self, request, *args, **kwargs ):
        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            raise BadRequest( 'Missing entity id in request.' )

        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )

        if not entity.can_user_delete:
            raise PermissionDenied( 'This entity cannot be deleted.' )
        
        context = {
            'entity': entity,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            raise BadRequest( 'Missing entity id.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )

        if not entity.can_user_delete:
            raise PermissionDenied( request, message = 'This entity cannot be deleted.' )
                
        entity.delete()

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )
    

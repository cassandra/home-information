import logging

from django.core.exceptions import BadRequest, PermissionDenied
from django.db import transaction
from django.urls import reverse
from django.utils.decorators import method_decorator

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.apps.entity.view_mixin import EntityViewMixin
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import LocationView

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
            return self.modal_response( request, context )

        with transaction.atomic():
            entity = entity_form.save()
            self._add_to_current_view_type(
                request = request,
                entity = entity,
            )
            
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    def _add_to_current_view_type( self, request, entity : Entity ):
        
        if request.view_parameters.view_type.is_location_view:
            try:
                current_location_view = LocationManager().get_default_location_view( request = request )
                EntityManager().add_entity_to_view(
                    entity = entity,
                    location_view = current_location_view,
                )
            except LocationView.DoesNotExist:
                logger.warning( 'No current location view to add new entity to.')

        elif request.view_parameters.view_type.is_collection:
            try:
                current_collection = CollectionManager().get_default_collection( request = request )
                CollectionManager().add_entity_to_collection(
                    entity = entity,
                    collection = current_collection,
                )
            except LocationView.DoesNotExist:
                logger.warning( 'No current collection to add new entity to.')
            
        else:
            logger.warning( 'No valid current view type to add new entity to.')

        return

    
@method_decorator( edit_required, name='dispatch' )
class EntityDeleteView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_delete.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        if not entity.can_user_delete:
            raise PermissionDenied( 'This entity cannot be deleted.' )
        
        context = {
            'entity': entity,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        if not entity.can_user_delete:
            raise PermissionDenied( request, message = 'This entity cannot be deleted.' )
                
        entity.delete()

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )
    

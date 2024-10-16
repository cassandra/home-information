import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import LocationView

from hi.decorators import edit_required
from hi.enums import ViewType
from hi.hi_async_view import HiModalView

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class CollectionAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'collection/edit/modals/collection_add.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'collection_form': forms.CollectionForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        collection_form = forms.CollectionForm( request.POST )
        if not collection_form.is_valid():
            context = {
                'collection_form': collection_form,
            }
            return self.modal_response( request, context )

        with transaction.atomic():
            collection = collection_form.save()
            self._add_to_location_view(
                request = request,
                collection = collection,
            )

        if request.view_parameters.view_type == ViewType.COLLECTION:
            request.view_parameters.update_collection( collection = collection )
            request.view_parameters.to_session( request )

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    def _add_to_location_view( self, request, collection : Collection ):
        try:
            # Ensure we have a location view to add the entity to.
            current_location_view = LocationManager().get_default_location_view( request = request )
            CollectionManager().create_collection_view(
                collection = collection,
                location_view = current_location_view,
            )
        except LocationView.DoesNotExist:
            logger.warning( 'No current location view to add new collection to.')

        return

    
@method_decorator( edit_required, name='dispatch' )
class CollectionDeleteView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'collection/edit/modals/collection_delete.html'

    def get(self, request, *args, **kwargs):
        try:
            collection_id = int( kwargs.get( 'collection_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location view id.' )
        try:
            collection = CollectionManager().get_collection(
                request = request,
                collection_id = collection_id,
            )
        except Collection.DoesNotExist:
            raise Http404( request )

        context = {
            'collection': collection,
        }
        return self.modal_response( request, context )

    def post( self, request, *args, **kwargs ):
        try:
            collection_id = int( kwargs.get( 'collection_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location view id.' )
        try:
            collection = CollectionManager().get_collection(
                request = request,
                collection_id = collection_id,
            )
        except Collection.DoesNotExist:
            raise Http404( request )

        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        collection.delete()

        if request.view_parameters.collection_id == collection_id:
            request.view_parameters.update_collection( collection = None )
            request.view_parameters.to_session( request )

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )
    

import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.enums import CollectionType
from hi.apps.collection.models import Collection

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

        cleaned_data = collection_form.clean()
        collection_type = CollectionType.from_name_safe( cleaned_data.get('collection_type') )
        name = cleaned_data.get('name')
        
        try:
            with transaction.atomic():
                collection = CollectionManager().create_collection(
                    request = request,
                    collection_type = collection_type,
                    name = name,
                )
                if ( request.view_parameters.view_type.is_location_view
                     and request.view_parameters.location_view_id ):
                    CollectionManager().create_collection_view_by_id(
                        collection = collection,
                        location_view_id = request.view_parameters.location_view_id,
                    )

        except ValueError as e:
            raise BadRequest( str(e) )

        if request.view_parameters.view_type == ViewType.COLLECTION:
            request.view_parameters.collection_id = collection.id
            request.view_parameters.to_session( request )

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class CollectionDeleteView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'collection/edit/modals/collection_delete.html'

    def get(self, request, *args, **kwargs):
        collection_id = kwargs.get( 'collection_id' )
        if not collection_id:
            raise BadRequest( 'No current collection found.' )
            
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            raise Http404( request )

        context = {
            'collection': collection,
        }
        return self.modal_response( request, context )

    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        collection_id = kwargs.get( 'collection_id' )
        if not collection_id:
            raise BadRequest( 'Missing collection id.' )
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            raise Http404( request )

        collection.delete()

        if request.view_parameters.view_type == ViewType.COLLECTION:
            next_collection = Collection.objects.all().order_by( 'order_id' ).first()
            if next_collection:
                request.view_parameters.collection_id = next_collection.id
            else:
                request.view_parameters.collection_id = None
            request.view_parameters.to_session( request )

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )
    

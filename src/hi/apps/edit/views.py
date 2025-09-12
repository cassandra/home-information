import json
import logging
import urllib.parse

from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.edit.views import (
    CollectionManageItemsView,
    CollectionReorder,
    CollectionReorderEntitiesView,
)
from hi.apps.control.models import Controller
from hi.apps.entity.models import EntityState
from hi.apps.location.edit.views import (
    LocationViewManageItemsView,
    LocationViewReorder,
)

from hi.decorators import edit_required
from hi.enums import ItemType, ViewMode
from hi.hi_async_view import HiModalView, HiSideView


logger = logging.getLogger(__name__)


class EditStartView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.
        
        if request.view_parameters.view_type.allows_edit_mode:
            redirect_url = request.META.get('HTTP_REFERER')
        else:
            redirect_url = None
        if not redirect_url:
            redirect_url = reverse('home')

        request.view_parameters.view_mode = ViewMode.EDIT
        request.view_parameters.to_session( request )
            
        return redirect( redirect_url )

    
class EditEndView( View ):

    def get(self, request, *args, **kwargs):

        # This must do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.

        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

        # Do a page refresh, but remove any side bar url set during editing.
        referrer_url = request.META.get('HTTP_REFERER')
        if referrer_url:
            parsed_url = urllib.parse.urlparse( referrer_url )
            query_params = urllib.parse.parse_qs( parsed_url.query )
            query_params[HiSideView.SIDE_URL_PARAM_NAME] = [ '' ]
            new_query_string = urllib.parse.urlencode(query_params, doseq=True)
            redirect_url = urllib.parse.urlunparse((
                '',
                '',
                parsed_url.path,
                parsed_url.params,
                new_query_string,
                parsed_url.fragment
            ))

        else:
            redirect_url = reverse('home')
            
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class ItemDetailsCloseView( View ):

    def get(self, request, *args, **kwargs ):
        if request.view_parameters.view_type.is_location_view:
            return LocationViewManageItemsView().get( request, *args, **kwargs )
            
        elif request.view_parameters.view_type.is_collection:
            return CollectionManageItemsView().get( request, *args, **kwargs )

        raise BadRequest( 'Add/remove items not supported for current view type.' )

    
@method_decorator( edit_required, name='dispatch' )
class ReorderItemsView( View ):

    def post( self, request, *args, **kwargs ):
        try:
            item_type_id_list = ItemType.parse_list_from_dict( request.POST )
        except (TypeError, ValueError ) as e:
            raise BadRequest( str(e) )

        try:
            item_types = set()
            item_id_list = list()
            for item_type, item_id in item_type_id_list:
                item_types.add( item_type )
                item_id_list.append( item_id )
                continue
        except ValueError as ve:
            raise BadRequest( str(ve) )
            
        if len(item_types) < 1:
            raise BadRequest( 'No ids found' )

        if len(item_types) > 1:
            raise BadRequest( f'Too many item types: {item_types}' )

        item_type = next(iter(item_types))
        if item_type == ItemType.ENTITY:
            if not request.view_parameters.view_type.is_collection:
                raise BadRequest( 'Entity reordering for collections only.' )
            return CollectionReorderEntitiesView().post(
                request,
                collection_id = request.view_parameters.collection_id,
                entity_id_list = json.dumps( item_id_list ),
            )

        elif item_type == ItemType.COLLECTION:
            return CollectionReorder().post(
                request,
                collection_id_list = json.dumps( item_id_list ),
            )

        elif item_type == ItemType.LOCATION_VIEW:
            return LocationViewReorder().post(
                request,
                location_view_id_list = json.dumps( item_id_list ),
            )

        else:
            raise BadRequest( f'Unknown item type: {item_type}' )


class EntityStateValueChoicesView( View ):

    def get( self, request, *args, **kwargs ):
        instance_name = kwargs.get( 'instance_name' )
        instance_id_str = kwargs.get( 'instance_id' )

        if not instance_name:
            raise BadRequest( 'Missing instance name.' )
        if not instance_id_str:
            raise BadRequest( 'Missing instance id.' )
        try:
            instance_id = int( instance_id_str )
        except (TypeError, ValueError):
            raise BadRequest( 'Instance id not an integer.' )

        if instance_name == 'entity_state':
            try:
                entity_state = EntityState.objects.get( id = instance_id )
            except EntityState.DoesNotExist:
                raise Http404( 'Unknown entity state.' )

        elif instance_name == 'controller':
            try:
                controller = Controller.objects.select_related('entity_state').get( id = instance_id )
                entity_state = controller.entity_state
            except Controller.DoesNotExist:
                raise Http404( 'Unknown controller.' )
            except EntityState.DoesNotExist:
                raise Http404( 'Unknown entity state.' )

        else:
            raise BadRequest( f'Unsupported instance name "{instance_name}".' )

        return HttpResponse( json.dumps( entity_state.choices() ),
                             content_type='application/json' )

import logging
import re
from typing import Any, Dict, Optional

from django.core.exceptions import BadRequest, PermissionDenied
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
import hi.apps.common.antinode as antinode
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.entity_pairing_manager import EntityPairingManager, EntityPairingError
from hi.apps.entity.edit.entity_type_transition_handler import EntityTypeTransitionHandler
from hi.apps.entity.forms import EntityForm
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.entity.view_mixins import EntityViewMixin
from hi.apps.location.models import LocationView
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.svg_item_factory import SvgItemFactory

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.hi_async_view import HiModalView, HiSideView

from . import forms

logger = logging.getLogger(__name__)


class EntityEditModeView( HiSideView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/panes/entity_edit_mode_panel.html'

    def should_push_url( self ) -> bool:
        return True
    
    def get_template_context( self,
                              request : HttpRequest,
                              *args   : Any,
                              **kwargs: Any          ) -> Dict[str, Any]:
        entity: Entity = self.get_entity( request, *args, **kwargs )

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = LocationManager().get_default_location_view( request = request )

        entity_edit_mode_data = EntityManager().get_entity_edit_mode_data(
            entity = entity,
            location_view = current_location_view,
            is_editing = request.view_parameters.is_editing,
        )
        return entity_edit_mode_data.to_template_context()


@method_decorator( edit_required, name='dispatch' )
class EntityAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_add.html'
    
    def get( self, request, *args, **kwargs ):
        context = {
            'entity_form': EntityForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        entity_form = EntityForm( request.POST )
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
            raise PermissionDenied( 'This entity cannot be deleted.' )
                
        entity.delete()

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )


@method_decorator( edit_required, name='dispatch' )
class EntityPositionEditView( View, EntityViewMixin ):

    def post(self, request, *args, **kwargs):
        entity = self.get_entity( request, *args, **kwargs )
        location = LocationManager().get_default_location( request = request )

        try:
            entity_position = EntityPosition.objects.get(
                entity = entity,
                location = location,
            )
        except EntityPosition.DoesNotExist:
            raise Http404( request )

        entity_position_form = forms.EntityPositionForm(
            location.svg_position_bounds,
            request.POST,
            instance = entity_position,
        )        
        if entity_position_form.is_valid():
            entity_position_form.save()
        else:
            logger.warning( 'EntityPosition form is invalid.' )
            
        context = {
            'entity': entity_position.entity,
            'entity_position_form': entity_position_form,
        }
        template = get_template( 'entity/edit/panes/entity_position_edit.html' )
        content = template.render( context, request = request )
        insert_map = {
            DIVID['ENTITY_POSITION_EDIT_PANE']: content,
        }

        svg_icon_item = SvgItemFactory().create_svg_icon_item(
            item = entity_position.entity,
            position = entity_position,
            css_class = '',
        )
        set_attributes_map = {
            svg_icon_item.html_id: {
                'transform': svg_icon_item.transform_str,
            }
        }
        return antinode.response(
            insert_map = insert_map,
            set_attributes_map = set_attributes_map,
        )


@method_decorator( edit_required, name='dispatch' )
class ManagePairingsView( HiModalView, EntityViewMixin ):

    ENTITY_PAIR_ID_NAME_PREFIX = 'entity-pair-id-'

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/manage_pairings.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        entity_pairing_manager = EntityPairingManager()
        entity_pairings = entity_pairing_manager.get_entity_pairing_list( entity = entity )
        candidate_entities = entity_pairing_manager.get_candidate_entities( entity = entity )

        existing_entities = [ x.paired_entity for x in entity_pairings ]
        entity_view_group_list = EntityManager().create_entity_view_group_list(
            existing_entities = existing_entities,
            all_entities = candidate_entities,
        )
        context = {
            'entity': entity,
            'entity_view_group_list': entity_view_group_list,
            'principal_entity_id_name_prefix': self.ENTITY_PAIR_ID_NAME_PREFIX,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        desired_paired_entity_ids = set()
        for name, value in request.POST.items():
            m = re.match( r'(\D+)(\d+)', name )
            if not m:
                continue
            prefix = m.group(1)
            if prefix == self.ENTITY_PAIR_ID_NAME_PREFIX:
                desired_paired_entity_ids.add( int( m.group(2) ))
            continue

        try:
            EntityPairingManager().adjust_entity_pairings(
                entity = entity,
                desired_paired_entity_ids = desired_paired_entity_ids,
            )
            return antinode.refresh_response()
        except EntityPairingError as epe:
            raise BadRequest( str(epe) )


class EntityPropertiesEditView( View, EntityViewMixin ):
    """Handle entity properties editing (name, type) only - used by sidebar.
    
    Business logic is delegated to EntityTypeTransitionHandler following
    the "keep views simple" design philosophy.
    """

    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity( request, *args, **kwargs )
        
        # Store original entity_type_str to detect changes
        original_entity_type_str: str = entity.entity_type_str

        entity_form = EntityForm( request.POST, instance = entity )
        form_valid: bool = entity_form.is_valid()
        
        if form_valid:
            # Delegate transition handling to specialized handler
            transition_handler = EntityTypeTransitionHandler()
            
            transition_response: Optional[HttpResponse] = transition_handler.handle_entity_form_save(
                request, entity, entity_form, None, original_entity_type_str
            )
            
            # Now that transaction is committed, handle any transition response
            if transition_response is not None:
                return transition_response
            
            status_code: int = 200
        else:
            status_code: int = 400

        context: Dict[str, Any] = {
            'entity': entity,
            'entity_form': entity_form,
        }
        template = get_template( 'entity/edit/panes/entity_properties_edit.html' )
        content: str = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['ENTITY_PROPERTIES_PANE']: content,
            },
            status = status_code,
        )

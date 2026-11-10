import logging
import re
from typing import Any, Dict, List, Optional, Set

from django.core.exceptions import BadRequest, PermissionDenied
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
import hi.apps.common.antinode as antinode
from hi.apps.common.svg_models import SvgViewBox
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.entity_pairing_manager import EntityPairingManager, EntityPairingError
from hi.apps.entity.entity_placement import EntityPlacer
from hi.apps.entity.edit.entity_type_transition_handler import EntityTypeTransitionHandler
from hi.apps.entity.forms import EntityAddForm, EntityForm
from hi.apps.entity.models import (
    ArchivedEntity,
    ArchivedEntityAttribute,
    Entity,
    EntityPosition,
)
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
class EntityAddView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_add.html'
    
    def get( self, request, *args, **kwargs ):
        context = {
            'entity_form': EntityAddForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        entity_form = EntityAddForm( request.POST )
        if not entity_form.is_valid():
            context = {
                'entity_form': entity_form,
            }
            return self.modal_response( request, context )

        # Preserve the user's current pan/zoom both for the post-add reload
        # (query params, below) and for where the new items are placed.
        svg_view_box_override = request.view_parameters.last_svg_view_box

        with transaction.atomic():
            created_entities = self._create_entities_bulk( entity_form = entity_form )
            for i, entity in enumerate( created_entities ):
                self._add_to_current_view_type(
                    request = request,
                    entity = entity,
                    bulk_grid_index = i,
                    bulk_grid_total = len( created_entities ),
                    svg_view_box_override = svg_view_box_override,
                )
                continue

        return self.redirect_home_w_geometry( request )

    def _create_entities_bulk(self, entity_form: EntityAddForm) -> List[Entity]:
        base_name = entity_form.cleaned_data['name']
        entity_type_str = entity_form.cleaned_data['entity_type_str']
        quantity = entity_form.cleaned_data['quantity']

        # Use create() in a loop rather than bulk_create() to ensure
        # save() overrides and post_save signal handlers fire. At the
        # 100-entity cap this is fast enough and avoids subtle bugs if
        # save-time side effects are added to Entity in the future.
        created_entities = []
        for i in range( 1, quantity + 1 ):
            entity_name = base_name if quantity == 1 else f'{base_name} ({i})'
            entity = Entity.objects.create(
                name=entity_name,
                entity_type_str=entity_type_str,
            )
            created_entities.append(entity)
            continue

        return created_entities

    def _add_to_current_view_type( self,
                                   request,
                                   entity : Entity,
                                   bulk_grid_index : Optional[int] = None,
                                   bulk_grid_total : Optional[int] = None,
                                   svg_view_box_override : Optional[SvgViewBox] = None ):

        if request.view_parameters.view_type.is_location_view:
            try:
                current_location_view = LocationManager().get_default_location_view( request = request )
                EntityPlacer().place_entity_in_view(
                    entity = entity,
                    location_view = current_location_view,
                    bulk_grid_index = bulk_grid_index,
                    bulk_grid_total = bulk_grid_total,
                    svg_view_box_override = svg_view_box_override,
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
            raise PermissionDenied( 'This item cannot be deleted.' )
        
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
            raise PermissionDenied( 'This item cannot be deleted.' )
                
        entity.delete()

        return self.redirect_home_w_geometry( request )


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

    """Pairs an entity with others. A principal with several states can
    go on to a grid that picks which of its states each delegate
    receives (the "refine" step) before submitting."""

    ENTITY_PAIR_ID_NAME_PREFIX = 'entity-pair-id-'
    ENTITY_PAIR_STATE_NAME_PREFIX = 'entity-pair-state-'

    ACTION_SUBMIT = 'submit'
    ACTION_REFINE = 'refine'
    ACTION_BACK = 'back'
    ACTION_SUBMIT_STATES = 'submit-states'

    STATE_GRID_TEMPLATE_NAME = 'entity/edit/modals/manage_pairing_states.html'

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/manage_pairings.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        return self._picker_response( request, entity = entity )

    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        action = request.POST.get( 'action', self.ACTION_SUBMIT )
        paired_entity_ids = self._get_posted_paired_entity_ids( request )

        if action == self.ACTION_REFINE:
            if not self._can_refine_states( entity ):
                raise BadRequest( f'States of {entity} cannot be refined.' )
            if not paired_entity_ids:
                return self._picker_response(
                    request,
                    entity = entity,
                    checked_entity_ids = paired_entity_ids,
                    message = 'Select at least one item to refine its states.',
                )
            return self._state_grid_response( request, entity = entity, paired_entity_ids = paired_entity_ids )

        if action == self.ACTION_BACK:
            return self._picker_response( request, entity = entity, checked_entity_ids = paired_entity_ids )

        try:
            if action == self.ACTION_SUBMIT_STATES:
                EntityPairingManager().set_delegated_states(
                    principal_entity = entity,
                    delegate_entity_id_to_state_ids = self._get_posted_delegate_state_ids(
                        request,
                        paired_entity_ids = paired_entity_ids,
                    ),
                )
            else:
                EntityPairingManager().adjust_entity_pairings(
                    entity = entity,
                    desired_paired_entity_ids = paired_entity_ids,
                )
            return antinode.refresh_response()
        except EntityPairingError as epe:
            raise BadRequest( str(epe) )

    def _can_refine_states( self, entity : Entity ) -> bool:
        return bool( entity.states.count() > 1 )

    def _picker_response( self,
                          request,
                          entity              : Entity,
                          checked_entity_ids  : Set[ int ]  = None,
                          message             : str         = None ):
        """The item picker. Items are checked per their current pairing
        unless checked_entity_ids carries the selection over from the
        refine step."""
        entity_pairing_manager = EntityPairingManager()
        entity_pairings = entity_pairing_manager.get_entity_pairing_list( entity = entity )
        candidate_entities = entity_pairing_manager.get_candidate_entities( entity = entity )

        if checked_entity_ids is None:
            checked_entities = [ x.paired_entity for x in entity_pairings ]
        else:
            checked_entities = [ x for x in candidate_entities if x.id in checked_entity_ids ]
        entity_view_group_list = EntityManager().create_entity_view_group_list(
            existing_entities = checked_entities,
            all_entities = candidate_entities,
        )
        context = {
            'entity': entity,
            'entity_view_group_list': entity_view_group_list,
            'entity_pairing_map': { x.paired_entity.id: x for x in entity_pairings },
            'principal_entity_id_name_prefix': self.ENTITY_PAIR_ID_NAME_PREFIX,
            'can_refine_states': self._can_refine_states( entity ),
            'message': message,
        }
        return self.modal_response( request, context )

    def _state_grid_response( self, request, entity : Entity, paired_entity_ids : Set[ int ] ):
        delegate_entities = list( Entity.objects.filter( id__in = paired_entity_ids ))
        pairing_state_grid = EntityPairingManager().get_pairing_state_grid(
            principal_entity = entity,
            delegate_entities = delegate_entities,
        )
        context = {
            'entity': entity,
            'pairing_state_grid': pairing_state_grid,
            'principal_entity_id_name_prefix': self.ENTITY_PAIR_ID_NAME_PREFIX,
            'entity_pair_state_name_prefix': self.ENTITY_PAIR_STATE_NAME_PREFIX,
        }
        return self.modal_response( request, context, template_name = self.STATE_GRID_TEMPLATE_NAME )

    def _get_posted_paired_entity_ids( self, request ) -> Set[ int ]:
        paired_entity_ids = set()
        for name in request.POST.keys():
            m = re.match( rf'^{self.ENTITY_PAIR_ID_NAME_PREFIX}(\d+)$', name )
            if m:
                paired_entity_ids.add( int( m.group(1) ))
            continue
        return paired_entity_ids

    def _get_posted_delegate_state_ids( self, request, paired_entity_ids : Set[ int ] ) -> Dict[ int, Set[ int ] ]:
        """Checked grid cells by delegate. Every grid row is posted as a
        paired entity id, so a row with no checked cells maps to no
        states (unpaired)."""
        delegate_entity_id_to_state_ids = { x: set() for x in paired_entity_ids }
        for name in request.POST.keys():
            m = re.match( rf'^{self.ENTITY_PAIR_STATE_NAME_PREFIX}(\d+)-(\d+)$', name )
            if not m:
                continue
            delegate_entity_id = int( m.group(1) )
            if delegate_entity_id not in delegate_entity_id_to_state_ids:
                raise BadRequest( f'State posted for an item not in the grid: {delegate_entity_id}' )
            delegate_entity_id_to_state_ids[delegate_entity_id].add( int( m.group(2) ))
            continue
        return delegate_entity_id_to_state_ids


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


@method_decorator( edit_required, name='dispatch' )
class EntityArchiveView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_archive.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        if entity.integration_id:
            raise PermissionDenied( 'Integration items cannot be archived.' )

        context = {
            'entity': entity,
        }
        return self.modal_response( request, context )

    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        if entity.integration_id:
            raise PermissionDenied( 'Integration items cannot be archived.' )

        with transaction.atomic():
            archived_entity = ArchivedEntity.objects.create(
                name = entity.name,
                entity_type_str = entity.entity_type_str,
                original_created_datetime = entity.created_datetime,
            )
            for attribute in entity.attributes.all():
                archived_attr = ArchivedEntityAttribute.objects.create(
                    archived_entity = archived_entity,
                    name = attribute.name,
                    value = attribute.value,
                    file_mime_type = attribute.file_mime_type,
                    value_type_str = attribute.value_type_str,
                    value_range_str = attribute.value_range_str,
                    attribute_type_str = attribute.attribute_type_str,
                    is_editable = False,
                    is_required = False,
                    order_id = attribute.order_id,
                )
                # Set file_value directly via update() to bypass save()'s
                # filename uniqueness logic, preserving the original file reference.
                if attribute.file_value:
                    ArchivedEntityAttribute.objects.filter(
                        pk = archived_attr.pk,
                    ).update( file_value = attribute.file_value.name )
                continue

            entity.delete()

        redirect_url = reverse( 'home' )
        return self.redirect_response( request, redirect_url )


class EntityArchiveListView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_archive_list.html'

    def get( self, request, *args, **kwargs ):
        archived_entities = ArchivedEntity.objects.all()
        context = {
            'archived_entities': archived_entities,
        }
        return self.modal_response( request, context )


class EntityArchiveDetailView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'entity/edit/modals/entity_archive_detail.html'

    def get( self, request, archived_entity_id, *args, **kwargs ):
        try:
            archived_entity = ArchivedEntity.objects.get( pk = archived_entity_id )
        except ArchivedEntity.DoesNotExist:
            raise Http404( 'Archived item not found.' )

        context = {
            'archived_entity': archived_entity,
            'attributes': archived_entity.attributes.all(),
        }
        return self.modal_response( request, context )

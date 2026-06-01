import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from hi.apps.common import datetimeproxy

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.entity.enums import DisplayContext
from hi.apps.entity.state_panel_dispatch import StatePanelDispatcher
from hi.apps.monitor.display_data import EntityDisplayData
from hi.apps.monitor.status_display_manager import StatusDisplayManager

from hi.enums import ViewDataPriority
from hi.integrations.integration_manager import IntegrationManager
from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView
from hi.apps.entity.edit.entity_type_transition_handler import EntityTypeTransitionHandler

from .entity_state_history import get_entity_state_history_page
from .entity_state_role_order import ENTITY_STATUS_VIEW_ORDERING
from .models import Entity, EntityAttribute
from .transient_models import EntityHistoryData
from hi.apps.entity.view_mixins import EntityStateViewMixin, EntityViewMixin
from .entity_attribute_edit_context import EntityAttributeItemEditContext


logger = logging.getLogger(__name__)


class EntityStatusView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_status.html'

    def get( self,
             request : HttpRequest,
             *args   : Any,
             **kwargs: Any          ) -> HttpResponse:
        entity = self.get_entity( request, *args, **kwargs )

        entity_status_data = StatusDisplayManager().get_entity_status_data( entity = entity )
        if not entity_status_data.entity_state_status_data_list:
            return EntityEditView().get( request, *args, **kwargs )

        entity_display_data = EntityDisplayData( entity_status_data = entity_status_data )
        debug = bool( request.GET.get( 'debug_panel' ) )
        state_panel_data = StatePanelDispatcher.build_state_panel_data(
            entity_display_data, DisplayContext.MODAL, debug = debug,
        )
        context = {
            'state_panel_data' : state_panel_data,
            'panel_trace'      : state_panel_data.trace if debug else None,
        }
        return self.modal_response( request, context )


class EntityHistoryView( HiModalView, EntityViewMixin ):
    """Per-entity overview modal. Renders one block per EntityState
    (the entity's own states plus delegated states) showing each
    state's most recent merged history rows. Each block links to
    the per-state EntityStateHistoryView for deeper navigation."""

    PER_STATE_ROW_COUNT = 5

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_history.html'

    def get( self, request, *args, **kwargs ):
        entity: Entity = self.get_entity( request, *args, **kwargs )

        states = list( entity.states.all() )
        for delegation in entity.entity_state_delegations.select_related('entity_state').all():
            if delegation.entity_state not in states:
                states.append( delegation.entity_state )
            continue

        states.sort( key = lambda s: ENTITY_STATUS_VIEW_ORDERING.sort_key(
            s.entity_state_role, entity.entity_type,
        ))

        state_to_rows : Dict[ Any, List[ Any ] ] = {}
        for state in states:
            rows = get_entity_state_history_page(
                entity_state = state,
                page_size = self.PER_STATE_ROW_COUNT,
            )
            state_to_rows[ state ] = rows[ : self.PER_STATE_ROW_COUNT ]
            continue

        entity_history_data = EntityHistoryData(
            entity = entity,
            state_to_rows = state_to_rows,
        )
        context: Dict[ str, Any ] = entity_history_data.to_template_context()
        return self.modal_response( request, context )


class EntityStateHistoryView( HiModalView, EntityStateViewMixin ):
    """Paginated per-EntityState merged history. The "History" anchor
    in the EntityStatus modal (both sensor and controller rows) and
    the "See All" link in the EntityHistoryView land here. Pagination
    is next/prev only, anchored on sensor observation timestamps with
    controller intents fetched in the same time range."""

    PAGE_SIZE = 25

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_state_history.html'

    def get( self, request, *args, **kwargs ):
        entity_state = self.get_entity_state( request, *args, **kwargs )

        before = _parse_iso_cursor( request.GET.get( 'before' ) )

        rows = get_entity_state_history_page(
            entity_state = entity_state,
            page_size = self.PAGE_SIZE,
            before = before,
        )

        # Multi-instrument source annotation surfaces only when the
        # state has more than one sensor or more than one controller,
        # i.e., when the row's instrument identity is ambiguous.
        multi_sensor = entity_state.sensors.count() > 1
        multi_controller = entity_state.controllers.count() > 1
        annotate_sources = multi_sensor or multi_controller

        # The oldest row's timestamp drives the "older" navigation
        # link; the cursor we paged from drives the "newer" link
        # back toward the most-recent page.
        older_cursor : Optional[ str ] = (
            datetimeproxy.datetime_to_iso_str( rows[ -1 ].timestamp )
            if rows else None
        )
        newer_cursor : Optional[ str ] = (
            datetimeproxy.datetime_to_iso_str( before )
            if before is not None else None
        )

        context = {
            'entity_state'      : entity_state,
            'history_rows'      : rows,
            'annotate_sources'  : annotate_sources,
            'older_cursor'      : older_cursor,
            'newer_cursor'      : newer_cursor,
        }
        return self.modal_response( request, context )


def _parse_iso_cursor( raw : Optional[ str ] ) -> Optional[ datetime ]:
    if not raw:
        return None
    try:
        return datetimeproxy.iso_str_to_datetime( raw )
    except ValueError:
        return None


class EntityEditView( HiModalView, EntityViewMixin, AttributeEditViewMixin ):
    """
    This view uses a dual response pattern:
      - get(): Returns full modal using standard modal_response()
      - post(): Returns custom JSON response with HTML fragments for async DOM updates
    """
    
    def get_template_name(self) -> str:
        return 'entity/modals/entity_edit.html'
    
    def get( self, request,*args, **kwargs ):
        priority_override = kwargs.pop( 'data_priority', None ) \
            or request.GET.get( 'data_priority' )
        entity = self.get_entity(request, *args, **kwargs)
        attr_item_context = EntityAttributeItemEditContext(
            entity = entity,
            extra_template_context = self._build_extra_template_context(
                entity,
                priority_override = priority_override,
            ),
        )
        template_context = self.create_initial_template_context(
            attr_item_context= attr_item_context,
        )
        return self.modal_response( request, template_context )

    def _build_extra_template_context(
            self, entity, priority_override : Optional[str] = None ) -> Dict[str, Any]:
        """Compute the entity-specific template variables (external
        view data, linked references, data priority) once. The
        result is stored on the AttributeItemEditContext and
        re-emitted by both the initial GET render and the async
        POST success render -- so the post-save modal refresh
        carries the same context as the initial open. (Active-tab
        persistence across the round-trip is handled client-side
        in attr.js, not via this initial data-priority value.)"""
        external_view_data = self._get_external_view_data( entity )
        external_references = entity.external_references.all()
        data_priority = self._resolve_data_priority(
            entity = entity,
            external_view_data = external_view_data,
            external_references = external_references,
            priority_override = priority_override,
        )
        return {
            'external_view_data': external_view_data,
            'external_references': external_references,
            'data_priority': data_priority,
        }

    @staticmethod
    def _resolve_data_priority( entity, external_view_data,
                                external_references,
                                priority_override : Optional[str] = None
                                ) -> ViewDataPriority:
        """Precedence: caller override (e.g., post-picker landing on
        Linked Content), then INTERNAL > EXTERNAL > REFERENCE. Falls
        back to INTERNAL when no category has content. An invalid
        override name silently falls through to the data-derived
        computation rather than erroring -- the override is an
        optional UX hint, not a contract."""
        if priority_override:
            override_value = ViewDataPriority.from_name_safe( priority_override )
            if override_value is not None:
                return override_value
        from hi.apps.attribute.enums import AttributeValueType
        file_type = str( AttributeValueType.FILE )
        has_files = entity.attributes.filter(
            value_type_str = file_type,
        ).exists()
        has_regulars = entity.attributes.exclude(
            value_type_str = file_type,
        ).exists()
        has_deleted = (
            EntityAttribute.deleted_objects.filter( entity = entity ).exists()
            if getattr( EntityAttribute, 'supports_soft_delete', False )
            else False
        )
        has_internal = has_files or has_regulars or has_deleted
        if has_internal:
            return ViewDataPriority.INTERNAL
        if external_view_data and external_view_data.has_content:
            return ViewDataPriority.EXTERNAL
        if external_references:
            return ViewDataPriority.REFERENCE
        return ViewDataPriority.default()

    def _get_external_view_data( self, entity ):
        if not entity.integration_id:
            return None
        try:
            gateway = IntegrationManager().get_integration_gateway( entity.integration_id )
        except KeyError:
            logger.warning(
                'No integration gateway registered for entity '
                f'{entity.id} (integration_id={entity.integration_id!r}).'
            )
            return None
        connector = gateway.get_connector()
        if connector is None:
            return None
        return connector.get_external_view_data( entity )

    def post( self, request,*args, **kwargs ):
        entity = self.get_entity(request, *args, **kwargs)
        original_entity_type = entity.entity_type
        attr_item_context = EntityAttributeItemEditContext(
            entity = entity,
            extra_template_context = self._build_extra_template_context( entity ),
        )
        response = self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )

        if response.status_code != 200:
            return response

        entity.refresh_from_db()
        entity_type_changed = bool( original_entity_type != entity.entity_type )
        if not entity_type_changed:
            return response

        transition_response = EntityTypeTransitionHandler().handle_entity_type_change(
            request = request,
            entity = entity,
        )
        if transition_response is None:
            return response

        return transition_response


class EntityAttributeUploadView( View, EntityViewMixin, AttributeEditViewMixin ):

    def post( self, request,*args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        attr_item_context = EntityAttributeItemEditContext(entity)
        return self.post_upload(
            request = request,
            attr_item_context = attr_item_context,
        )


class EntityAttributeHistoryInlineView( View, AttributeEditViewMixin ):
    """View for displaying EntityAttribute history inline within the edit modal."""

    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this entity for security
        try:
            attribute = EntityAttribute.objects.select_related('entity').get(
                pk = attribute_id, entity_id = entity_id )
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = EntityAttributeItemEditContext( entity = attribute.entity )
        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )


class EntityAttributeRestoreInlineView( View, AttributeEditViewMixin ):
    """View for restoring EntityAttribute values from history within the edit modal."""
    
    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             history_id   : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """

        try:
            attribute = EntityAttribute.objects.select_related('entity').get(
                pk = attribute_id, entity_id = entity_id )
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = EntityAttributeItemEditContext( entity = attribute.entity )
        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_item_context = attr_item_context,
        )


class EntityAttributeRestoreDeletedInlineView( View ):
    """View for restoring soft-deleted EntityAttributes."""

    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        try:
            attribute = EntityAttribute.deleted_objects.select_related('entity').get(
                pk = attribute_id,
                entity_id = entity_id,
            )
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Deleted attribute not found.")

        attribute.restore_from_deleted()
        attr_item_context = EntityAttributeItemEditContext( entity = attribute.entity )
        renderer = AttributeEditResponseRenderer()
        return renderer.render_form_success_response(
            attr_item_context = attr_item_context,
            request = request,
            message = 'Attribute restored',
        )

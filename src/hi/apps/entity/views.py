import logging

from django.db import transaction
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.location.location_manager import LocationManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin

from hi.hi_async_view import HiModalView, HiSideView
from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView

from .entity_manager import EntityManager
from . import forms
from .models import EntityAttribute
from .transient_models import EntityEditData, EntityStateHistoryData
from .view_mixins import EntityViewMixin

logger = logging.getLogger(__name__)


class BaseEntityEditMixin:
    """Shared logic for entity editing operations"""
    
    def _handle_entity_form_save(self, request, entity, entity_form, entity_attribute_formset=None, original_entity_type_str=None):
        """Handle saving entity form and optional formset with transition logic"""
        if original_entity_type_str is None:
            original_entity_type_str = entity.entity_type_str
        
        transition_response = None
        
        with transaction.atomic():
            entity_form.save()
            if entity_attribute_formset:
                entity_attribute_formset.save()
            
            # Handle transitions within same transaction but defer response
            entity_type_changed = original_entity_type_str != entity.entity_type_str
            if entity_type_changed:
                transition_response = self._handle_entity_type_change(request, entity)
        
        return transition_response
    
    def _recreate_fresh_formset(self, entity):
        """Recreate formset to preserve 'max' to show new form"""
        return forms.EntityAttributeFormSet(
            instance = entity,
            prefix = f'entity-{entity.id}',
        )
    
    def _handle_entity_type_change(self, request, entity):
        """Handle EntityType changes with appropriate transition logic"""
        try:
            # Always attempt advanced transition handling regardless of mode/view
            current_location_view = LocationManager().get_default_location_view( request = request )
            transition_occurred, transition_type = EntityManager().handle_entity_type_transition(
                entity = entity,
                location_view = current_location_view,
            )
            
            if self._needs_full_page_refresh(transition_occurred, transition_type):
                return antinode.refresh_response()
            
            # Simple transitions can continue with sidebar-only refresh
            # (will fall through to normal entity_edit_response)
            return None
            
        except Exception as e:
            logger.warning(f'EntityType transition failed: {e}, falling back to page refresh')
            return antinode.refresh_response()
    
    def _needs_full_page_refresh(self, transition_occurred, transition_type):
        """Determine if EntityType change requires full page refresh"""
        if not transition_occurred:
            # Transition failed, use page refresh for safety
            return True
            
        if transition_type == "path_to_path":
            # Path style changes only, sidebar refresh sufficient
            return False
            
        # All other transitions need full refresh to show visual changes:
        # - icon_to_icon: New icon type needs to be visible
        # - icon_to_path: Database structure changed
        # - path_to_icon: Database structure changed
        return True


class EntityEditView( BaseEntityEditMixin, View, EntityViewMixin ):
    """Handle full entity editing including attributes - used by modal"""

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        entity_edit_data = EntityEditData( entity = entity )
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
        )
    
    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        
        # Store original entity_type_str to detect changes
        original_entity_type_str = entity.entity_type_str

        entity_form = forms.EntityForm( request.POST, instance = entity )
        entity_attribute_formset = forms.EntityAttributeFormSet(
            request.POST,
            request.FILES,
            instance = entity,
            prefix = f'entity-{entity.id}',
        )
        
        form_valid = entity_form.is_valid() and entity_attribute_formset.is_valid()
        
        if form_valid:
            transition_response = self._handle_entity_form_save(
                request, entity, entity_form, entity_attribute_formset, original_entity_type_str
            )
            
            # Now that transaction is committed, handle any transition response
            if transition_response is not None:
                return transition_response
                
            # Recreate formset to preserve "max" to show new form
            entity_attribute_formset = self._recreate_fresh_formset(entity)
            status_code = 200
        else:
            status_code = 400
            
        entity_edit_data = EntityEditData(
            entity = entity,
            entity_form = entity_form,
            entity_attribute_formset = entity_attribute_formset,
        )
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
            status_code = status_code,
        )


class EntityPropertiesEditView( BaseEntityEditMixin, View, EntityViewMixin ):
    """Handle entity properties editing (name, type) only - used by sidebar"""

    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        
        # Store original entity_type_str to detect changes
        original_entity_type_str = entity.entity_type_str

        entity_form = forms.EntityForm( request.POST, instance = entity )
        form_valid = entity_form.is_valid()
        
        if form_valid:
            transition_response = self._handle_entity_form_save(
                request, entity, entity_form, None, original_entity_type_str
            )
            
            # Now that transaction is committed, handle any transition response
            if transition_response is not None:
                return transition_response
            
            status_code = 200
        else:
            status_code = 400
            
        # For properties editing, we create EntityEditData without formset
        entity_edit_data = EntityEditData(
            entity = entity,
            entity_form = entity_form,
            entity_attribute_formset = None,
        )
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
            status_code = status_code,
        )

        
class EntityAttributeUploadView( View, EntityViewMixin ):

    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        entity_attribute = EntityAttribute( entity = entity )
        entity_attribute_upload_form = forms.EntityAttributeUploadForm(
            request.POST,
            request.FILES,
            instance = entity_attribute,
        )

        if entity_attribute_upload_form.is_valid():
            with transaction.atomic():
                entity_attribute_upload_form.save()   
            status_code = 200
        else:
            status_code = 400

        entity_edit_data = EntityEditData(
            entity = entity,
            entity_attribute_upload_form = entity_attribute_upload_form,
        )            
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
            status_code = status_code,
        )

    
class EntityStatusView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_status.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        entity_status_data = StatusDisplayManager().get_entity_status_data( entity = entity )
        if not entity_status_data.entity_state_status_data_list:
            return EntityEditView().get( request, *args, **kwargs )
        
        context = entity_status_data.to_template_context()
        return self.modal_response( request, context )

    
class EntityStateHistoryView( HiModalView, EntityViewMixin, SensorHistoryMixin ):

    ENTITY_STATE_HISTORY_ITEM_MAX = 5
    
    def get_template_name( self ) -> str:
        return 'entity/modals/entity_state_history.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        sensor_history_list_map = self.sensor_history_manager().get_latest_entity_sensor_history(
            entity = entity,
            max_items = self.ENTITY_STATE_HISTORY_ITEM_MAX,
        )
        controller_history_list_map = ControllerHistoryManager().get_latest_entity_controller_history(
            entity = entity,
            max_items = self.ENTITY_STATE_HISTORY_ITEM_MAX,
        )        
        entity_state_history_data = EntityStateHistoryData(
            entity = entity,
            sensor_history_list_map = sensor_history_list_map,
            controller_history_list_map = controller_history_list_map,
        )
        context = entity_state_history_data.to_template_context()
        return self.modal_response( request, context )


class EntityDetailsView( HiSideView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/panes/entity_edit_mode_panel.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = LocationManager().get_default_location_view( request = request )

        entity_details_data = EntityManager().get_entity_details_data(
            entity = entity,
            location_view = current_location_view,
            is_editing = request.view_parameters.is_editing,
        )
        return entity_details_data.to_template_context()


class EntityAttributeHistoryView(BaseAttributeHistoryView):
    """View for displaying EntityAttribute history in a modal."""
    
    def get_attribute_model_class(self):
        return EntityAttribute
    
    def get_history_url_name(self):
        return 'entity_attribute_history'
    
    def get_restore_url_name(self):
        return 'entity_attribute_restore'


class EntityAttributeRestoreView(BaseAttributeRestoreView):
    """View for restoring EntityAttribute values from history."""
    
    def get_attribute_model_class(self):
        return EntityAttribute

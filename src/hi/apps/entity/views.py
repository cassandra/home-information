import logging

from django.db import transaction
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.location.location_manager import LocationManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin

from hi.hi_async_view import HiModalView, HiSideView

from .entity_manager import EntityManager
from . import forms
from .models import EntityAttribute
from .transient_models import EntityEditData, EntityStateHistoryData
from .view_mixins import EntityViewMixin

logger = logging.getLogger(__name__)


class EntityEditView( View, EntityViewMixin ):

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
        if entity_form.is_valid() and entity_attribute_formset.is_valid():
            with transaction.atomic():
                entity_form.save()   
                entity_attribute_formset.save()
                
            # Check if EntityType changed and handle transitions
            if original_entity_type_str != entity.entity_type_str:
                # Try advanced transition handling if in editing mode
                if request.view_parameters.is_editing and request.view_parameters.view_type.is_location_view:
                    try:
                        current_location_view = LocationManager().get_default_location_view( request = request )
                        transition_occurred, transition_type = EntityManager().handle_entity_type_transition(
                            entity = entity,
                            location_view = current_location_view,
                        )
                        
                        if transition_occurred and transition_type in ["icon_to_icon", "path_to_path"]:
                            # These transitions only need visual updates, can continue with sidebar refresh
                            pass
                        elif transition_occurred:
                            # Database structure changed, need full page refresh
                            return antinode.refresh_response()
                        else:
                            # Transition failed, fallback to page refresh
                            return antinode.refresh_response()
                            
                    except Exception as e:
                        logger.warning(f'EntityType transition failed: {e}, falling back to page refresh')
                        return antinode.refresh_response()
                else:
                    # Not in editing mode or not in location view, use simple page refresh
                    return antinode.refresh_response()
                
            # Recreate to preserve "max" to show new form
            entity_attribute_formset = forms.EntityAttributeFormSet(
                instance = entity,
                prefix = f'entity-{entity.id}',
            )
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
        return 'entity/edit/panes/entity_details.html'

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

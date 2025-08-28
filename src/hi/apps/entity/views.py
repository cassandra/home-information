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
from hi.apps.attribute.enums import AttributeValueType

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
            # (will fall through to normal response method)
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
        return self.entity_modal_response(
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
        return self.entity_modal_response(
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
        return self.entity_properties_response(
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
            
            # Render new file card HTML to append to file grid
            from django.template.loader import render_to_string
            file_card_html = render_to_string(
                'attribute/components/v2/file_card.html',
                {'attribute': entity_attribute}
            )
            
            return antinode.response(
                append_map={
                    'attr-v2-file-grid': file_card_html
                }
            )
        else:
            # Render error message to status area
            from django.template.loader import render_to_string
            error_html = render_to_string(
                'attribute/components/v2/status_message.html',
                {
                    'error_message': 'File upload failed. Please check the file and try again.',
                    'form_errors': entity_attribute_upload_form.errors
                }
            )
            
            return antinode.response(
                insert_map={
                    'attr-v2-status-msg': error_html
                },
                status=400
            )

    
class EntityStatusView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_status.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        entity_status_data = StatusDisplayManager().get_entity_status_data( entity = entity )
        if not entity_status_data.entity_state_status_data_list:
            return EntityEditV2View().get( request, *args, **kwargs )
        
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


class EntityEditV2View(HiModalView, EntityViewMixin):
    """V2 Entity attribute editing modal with redesigned interface."""
    
    def get_template_name(self) -> str:
        return 'entity/modals/entity_edit_v2.html'
    
    def get(self, request, *args, **kwargs):
        entity = self.get_entity(request, *args, **kwargs)
        
        # Get entity form
        from hi.apps.entity.forms import EntityForm
        entity_form = EntityForm(instance=entity)
        
        # Get file attributes for display (not a formset, just for template rendering)
        from hi.apps.attribute.enums import AttributeValueType
        file_attributes = entity.attributes.filter(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id')
        
        # Regular attributes formset (automatically excludes FILE attributes)
        from hi.apps.entity.forms import EntityAttributeRegularFormSet
        property_attributes_formset = EntityAttributeRegularFormSet(
            instance=entity,
            prefix=f'entity-{entity.id}'
        )
        
        context = {
            'entity': entity,
            'entity_form': entity_form,
            'file_attributes': file_attributes,
            'property_attributes_formset': property_attributes_formset,
        }
        
        return self.modal_response(request, context)
    
    def post(self, request, *args, **kwargs):
        entity = self.get_entity(request, *args, **kwargs)
        
        from hi.apps.entity.forms import EntityForm, EntityAttributeRegularFormSet
        
        # Handle form submission
        entity_form = EntityForm(request.POST, instance=entity)
        
        # Regular attributes formset (automatically excludes FILE attributes)
        property_attributes_formset = EntityAttributeRegularFormSet(
            request.POST,
            instance=entity,
            prefix=f'entity-{entity.id}'
        )
        
        # Log form data for debugging
        logger.info(f'POST data received: {dict(request.POST)}')
        logger.info(f'Entity form is_valid: {entity_form.is_valid()}')
        logger.info(f'Formset is_valid: {property_attributes_formset.is_valid()}')
        
        if entity_form.is_valid() and property_attributes_formset.is_valid():
            with transaction.atomic():
                entity_form.save()
                property_attributes_formset.save()
                
                # Process file deletions
                file_deletes = request.POST.getlist('delete_file_attribute')
                if file_deletes:
                    logger.info(f'Processing file deletions: {file_deletes}')
                    for attr_id in file_deletes:
                        if attr_id:  # Skip empty values
                            try:
                                file_attribute = EntityAttribute.objects.get(
                                    id=attr_id, 
                                    entity=entity,
                                    value_type_str=str(AttributeValueType.FILE)
                                )
                                # Verify permission to delete
                                if file_attribute.attribute_type.can_delete:
                                    logger.info(f'Deleting file attribute {attr_id}: {file_attribute.name}')
                                    file_attribute.delete()
                                else:
                                    logger.warning(f'File attribute {attr_id} cannot be deleted - permission denied')
                            except EntityAttribute.DoesNotExist:
                                logger.warning(f'File attribute {attr_id} not found or not owned by entity {entity.id}')
            
            # Return success response using antinode helpers
            return self._render_success_response(entity)
        else:
            # Debug logging for validation errors
            if not entity_form.is_valid():
                logger.warning(f'Entity form validation failed: {entity_form.errors}')
                logger.warning(f'Entity form cleaned_data: {getattr(entity_form, "cleaned_data", "N/A")}')
            if not property_attributes_formset.is_valid():
                logger.warning(f'Formset validation failed: {property_attributes_formset.errors}')
                logger.warning(f'Formset non-form errors: {property_attributes_formset.non_form_errors()}')
            
            # Return validation errors using antinode helpers
            return self._render_error_response(entity, entity_form, property_attributes_formset)
    
    def get_success_url_name(self) -> str:
        return 'entity_edit_v2'
    
    def _render_success_response(self, entity):
        """Render success response using antinode helpers - multiple target replacement"""
        # Re-render both content body and upload form
        content_body, upload_form = self._render_fragments(entity, success_message="Changes saved successfully")
        
        return antinode.response(
            insert_map={
                'attr-v2-content': content_body,
                'attr-v2-upload-form-container': upload_form
            }
        )
    
    def _render_error_response(self, entity, entity_form, property_attributes_formset):
        """Render error response using antinode helpers - multiple target replacement"""
        # Re-render both content body and upload form with form errors
        content_body, upload_form = self._render_fragments(
            entity, 
            entity_form=entity_form, 
            property_attributes_formset=property_attributes_formset, 
            error_message="Please correct the errors below",
            has_errors=True
        )
        
        return antinode.response(
            insert_map={
                'attr-v2-content': content_body,
                'attr-v2-upload-form-container': upload_form
            },
            status=400
        )
    
    def _render_fragments(self, entity, entity_form=None, property_attributes_formset=None, success_message=None, error_message=None, has_errors=False):
        """Render both content body and upload form fragments"""
        from django.template.loader import render_to_string
        
        # If forms not provided, create fresh ones (for success case)
        if entity_form is None:
            from hi.apps.entity.forms import EntityForm
            entity_form = EntityForm(instance=entity)
            
        if property_attributes_formset is None:
            from hi.apps.entity.forms import EntityAttributeRegularFormSet
            property_attributes_formset = EntityAttributeRegularFormSet(
                instance=entity,
                prefix=f'entity-{entity.id}'
            )
        
        # Get file attributes
        from hi.apps.attribute.enums import AttributeValueType
        file_attributes = entity.attributes.filter(value_type_str=str(AttributeValueType.FILE)).order_by('id')
        
        # Collect non-field errors for enhanced error messaging
        non_field_errors = []
        
        # Entity form non-field errors
        if entity_form and hasattr(entity_form, 'non_field_errors') and entity_form.non_field_errors():
            non_field_errors.extend([f"Entity: {error}" for error in entity_form.non_field_errors()])
        
        # Property formset non-field errors
        if property_attributes_formset and hasattr(property_attributes_formset, 'non_field_errors') and property_attributes_formset.non_field_errors():
            non_field_errors.extend([f"Properties: {error}" for error in property_attributes_formset.non_field_errors()])
        
        # Individual property form non-field errors
        if property_attributes_formset:
            for i, form in enumerate(property_attributes_formset.forms):
                if hasattr(form, 'non_field_errors') and form.non_field_errors():
                    property_name = form.instance.name if form.instance.pk else f"New Property #{i+1}"
                    non_field_errors.extend([f"{property_name}: {error}" for error in form.non_field_errors()])
        
        # Debug logging
        logger.info(f'Rendering fragments for entity {entity.id}')
        logger.info(f'File attributes count: {file_attributes.count()}')
        if property_attributes_formset:
            logger.info(f'Property formset total forms: {property_attributes_formset.total_form_count()}')
            logger.info(f'Property formset is bound: {property_attributes_formset.is_bound}')
            logger.info(f'Property formset is valid: {property_attributes_formset.is_valid()}')
        if non_field_errors:
            logger.info(f'Non-field errors collected: {non_field_errors}')
        
        # Context for both fragments
        context = {
            'entity': entity,
            'entity_form': entity_form,
            'file_attributes': file_attributes,
            'property_attributes_formset': property_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_field_errors': non_field_errors,
        }
        
        # Render both fragments
        content_body = render_to_string('attribute/components/v2/content_body.html', context)
        
        # Upload form needs to be specific to entity
        upload_form = render_to_string(
            'attribute/components/v2/upload_form.html',
            {'entity': entity}
        )
        
        return content_body, upload_form

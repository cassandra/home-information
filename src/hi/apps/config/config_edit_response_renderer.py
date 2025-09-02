"""
ConfigEditResponseRenderer - Handles template rendering and response generation for config settings editing.
Adapted from Entity/Location patterns for page-based (non-modal) context.
"""
from typing import Any, Dict, List, Optional

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

import hi.apps.common.antinode as antinode
from hi.constants import DIVID
from .config_edit_form_handler import ConfigEditFormHandler
from .forms import SubsystemAttributeFormSet
from .subsystem_attribute_edit_context import SubsystemAttributeEditContext
from .subsystem_attribute_edit_data import SubsystemAttributeEditData


class ConfigEditResponseRenderer:
    """Handles template rendering and response generation for config settings editing."""

    def __init__(self) -> None:
        self.form_handler = ConfigEditFormHandler()

    def build_template_context(
            self,
            subsystem_formset_list: List[SubsystemAttributeFormSet],
            success_message: Optional[str] = None,
            error_message: Optional[str] = None,
            has_errors: bool = False,
            selected_subsystem_id: str = None
    ) -> Dict[str, Any]:
        """Build context dictionary for template rendering."""
        
        # Create paired data objects with formsets and their contexts
        subsystem_edit_data_list = []
        for formset in subsystem_formset_list:
            # Count errors for this subsystem
            error_count = 0
            for form in formset:
                if form.errors:
                    error_count += len(form.errors)
            
            # Create data object with error count
            subsystem_data = SubsystemAttributeEditData(
                formset=formset,
                context=SubsystemAttributeEditContext(formset.instance),
                error_count=error_count
            )
            subsystem_edit_data_list.append(subsystem_data)
        
        # Determine selected subsystem ID (default to first if none provided)
        if selected_subsystem_id is None and subsystem_formset_list:
            selected_subsystem_id = str(subsystem_formset_list[0].instance.id)
        
        context = {
            'subsystem_edit_data_list': subsystem_edit_data_list,
            'selected_subsystem_id': selected_subsystem_id,
            'history_url_name': 'config_attribute_history',
            'restore_url_name': 'config_attribute_restore',
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
        }
        
        return context

    def render_success_response(
            self,
            request: HttpRequest,
            selected_subsystem_id: str = None
    ) -> HttpResponse:
        """Render success response using antinode helpers for flexible DOM updates.
        
        Returns an antinode response that can update multiple DOM targets,
        providing flexibility for future enhancements like file uploads.
        """
        # Create fresh formsets to show updated state
        subsystem_formset_list = self.form_handler.create_config_forms()
        
        context = self.build_template_context(
            subsystem_formset_list,
            success_message="Settings saved successfully",
            selected_subsystem_id=selected_subsystem_id
        )
        
        # Render the content body that gets replaced
        content_html = render(request, 'config/panes/config_settings_content_body.html', context).content.decode('utf-8')
        
        # Use antinode response with proper DIVID key (not selector)
        # This replaces the content inside the element with id="attr-v2-content"
        return antinode.response(
            insert_map={
                DIVID['ATTR_V2_CONTENT']: content_html,
                # Future: Can add DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER'] for file uploads
            }
        )

    def render_error_response(
            self,
            request: HttpRequest,
            subsystem_formset_list: List[SubsystemAttributeFormSet],
            selected_subsystem_id: str = None
    ) -> HttpResponse:
        """Render error response with validation errors and user input preserved."""
        
        # Collect error information for better user feedback
        error_count = 0
        for formset in subsystem_formset_list:
            for form in formset:
                if form.errors:
                    error_count += len(form.errors)
        
        error_message = "Please correct the errors below." if error_count > 0 else "Validation failed."
        
        context = self.build_template_context(
            subsystem_formset_list,
            error_message=error_message,
            has_errors=True,
            selected_subsystem_id=selected_subsystem_id
        )
        
        # Render the content body with error state
        content_html = render(request, 'config/panes/config_settings_content_body.html', context).content.decode('utf-8')
        
        # Use antinode response for consistent behavior
        return antinode.response(
            insert_map={
                DIVID['ATTR_V2_CONTENT']: content_html,
            }
        )

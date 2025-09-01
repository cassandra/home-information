"""
ConfigEditResponseRenderer - Handles template rendering and response generation for config settings editing.
Adapted from Entity/Location patterns for page-based (non-modal) context.
"""
from typing import Any, Dict, List, Optional

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

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
            has_errors: bool = False
    ) -> Dict[str, Any]:
        """Build context dictionary for template rendering."""
        
        # Create paired data objects with formsets and their contexts
        subsystem_edit_data_list = [
            SubsystemAttributeEditData(
                formset=formset,
                context=SubsystemAttributeEditContext(formset.instance)
            )
            for formset in subsystem_formset_list
        ]
        
        context = {
            'subsystem_edit_data_list': subsystem_edit_data_list,
            'history_url_name': 'config_attribute_history',
            'restore_url_name': 'config_attribute_restore',
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
        }
        
        return context

    def render_success_response(
            self,
            request: HttpRequest
    ) -> HttpResponse:
        """Render success response with fresh form data and success message."""
        # Create fresh formsets to show updated state
        subsystem_formset_list = self.form_handler.create_config_forms()
        
        context = self.build_template_context(
            subsystem_formset_list,
            success_message="Settings saved successfully"
        )
        
        return render(request, 'config/panes/system_settings_redesigned.html', context)

    def render_error_response(
            self,
            request: HttpRequest,
            subsystem_formset_list: List[SubsystemAttributeFormSet]
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
            has_errors=True
        )
        
        return render(request, 'config/panes/system_settings_redesigned.html', context)

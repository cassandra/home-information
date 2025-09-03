import logging
from typing import Any, Dict, Optional, Tuple

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

from .edit_context import AttributeEditContext
from .edit_form_handler import AttributeEditFormHandler
from .response_helpers import AttributeResponseBuilder, UpdateMode
from .response_constants import DefaultMessages
from .transient_models import AttributeEditFormData

logger = logging.getLogger(__name__)


class AttributeEditResponseRenderer:
    """
    Handles template rendering and response generation for attribute editing.
    
    This class encapsulates business logic for:
    - Building template contexts
    - Rendering template fragments for HTMX updates
    - Constructing antinode responses for success/error cases
    """

    def __init__(self) -> None:
        self.form_handler = AttributeEditFormHandler()
        return
    
    def render_success_response( self,
                                 attr_context  : AttributeEditContext,
                                 request : HttpRequest      ) -> HttpResponse:
        """Render success response using custom JSON format - multiple target replacement.
        Returns:
            HttpResponse: Success response with JSON format for custom Ajax handling
        """
        # Re-render both content body and upload form with fresh forms
        content_body, upload_form = self.render_update_fragments(
            attr_context = attr_context, 
            request = request,
            success_message = DefaultMessages.SAVE_SUCCESS
        )
        return (
            AttributeResponseBuilder()
            .success()
            .add_update(
                target=f"#{attr_context.content_html_id}",
                html=content_body,
                mode=UpdateMode.REPLACE
            ).add_update(
                target=f"#{attr_context.upload_form_container_html_id}",
                html=upload_form,
                mode=UpdateMode.REPLACE
            )
            .with_message(DefaultMessages.SAVE_SUCCESS)
            .build_http_response()
        )

    def render_error_response( self,
                               attr_context    : AttributeEditContext,
                               edit_form_data  : AttributeEditFormData,
                               request         : HttpRequest           ) -> HttpResponse:
        """Render error response using custom JSON format - multiple target replacement.
        Returns:
            HttpResponse: Error response with JSON format for custom Ajax handling
        """
        # Re-render both content body and upload form with form errors
        content_body, upload_form = self.render_update_fragments(
            attr_context = attr_context,
            request = request,
            edit_form_data = edit_form_data,
            error_message = DefaultMessages.SAVE_ERROR,
            has_errors = True,
        )
        return (
            AttributeResponseBuilder()
            .error()
            .add_update(
                target=f"#{attr_context.content_html_id}",
                html=content_body,
                mode=UpdateMode.REPLACE
            )
            .add_update(
                target=f"#{attr_context.upload_form_container_html_id}",
                html=upload_form,
                mode=UpdateMode.REPLACE
            )
            .with_message(DefaultMessages.SAVE_ERROR)
            .build_http_response()
        )
    
    def render_update_fragments( self,
                                 attr_context     : AttributeEditContext,
                                 request          : HttpRequest,
                                 edit_form_data   : AttributeEditFormData  = None,
                                 success_message  : Optional[str]          = None,
                                 error_message    : Optional[str]          = None,
                                 has_errors       : bool                   = False ) -> Tuple[str, str]:
        """Render both content body and upload form fragments for antinode updates.
        
        This is the main method for generating fragment updates after form submissions.
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # If forms not provided, create fresh ones (for success case)
        fresh_form_data = self.form_handler.create_edit_form_data( attr_context= attr_context )
        if edit_form_data:
            if edit_form_data.owner_form is None:
                edit_form_data.owner_form = fresh_form_data.owner_form
            if edit_form_data.regular_attributes_formset is None:
                edit_form_data.regular_attributes_formset = fresh_form_data.regular_attributes_formset
            if edit_form_data.file_attributes is None:
                edit_form_data.file_attributes = fresh_form_data.file_attributes
        else:
            edit_form_data = fresh_form_data
            
        template_context = self.build_template_context(
            attr_context = attr_context,
            edit_form_data = edit_form_data,
            success_message = success_message,
            error_message = error_message,
            has_errors= has_errors,
        )
        return self.render_content_fragments(
            attr_context = attr_context,
            request = request,
            template_context = template_context,
        )

    def render_content_fragments( self,
                                  attr_context      : AttributeEditContext,
                                  template_context  : Dict[str, Any],
                                  request           : HttpRequest         ) -> Tuple[str, str]:
        """Render both content body and upload form fragments.
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # Render both fragments
        content_body = render_to_string(
            attr_context.content_body_template_name,
            template_context,
            request = request,
        )        
        upload_form = render_to_string(
            'attribute/components/upload_form.html',
            {
                'file_upload_url': attr_context.file_upload_url,
                'attr_context': attr_context
            },
            request = request,  # Needed for context processors (CSRF, DIVID, etc.)
        )
        return content_body, upload_form
    
    def build_template_context( self,
                                attr_context     : AttributeEditContext,
                                edit_form_data   : AttributeEditFormData,
                                success_message  : Optional[str]          = None,
                                error_message    : Optional[str]          = None,
                                has_errors       : bool                   = False ) -> Dict[str, Any]:
        """
        Returns:
            dict: Template context with all required variables
        """
        non_field_errors = self.form_handler.collect_form_errors( edit_form_data = edit_form_data )
        
        # Build context with both old and new patterns for compatibility
        context = {
            'owner_form': edit_form_data.owner_form,
            'file_attributes': edit_form_data.file_attributes,
            'regular_attributes_formset': edit_form_data.regular_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_field_errors': non_field_errors,
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update( attr_context.to_template_context() )
        
        return context

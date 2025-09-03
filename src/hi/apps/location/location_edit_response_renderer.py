"""
LocationEditResponseRenderer - Handles template rendering and response generation for location editing.

This class follows the same pattern as EntityEditResponseRenderer, encapsulating the complex 
rendering and response logic that was previously embedded in LocationEditView, following 
the "keep views simple" design philosophy.
"""
from typing import Any, Dict, Optional, Tuple
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse

from hi.apps.attribute.response_helpers import AttributeResponseBuilder, UpdateMode
from hi.apps.attribute.response_constants import DefaultMessages
from django.http import HttpResponse
from hi.constants import DIVID
from .location_edit_form_handler import LocationEditFormHandler
from .models import Location, LocationAttribute
from .forms import LocationAttributeRegularFormSet, LocationForm
from .location_attribute_edit_context import LocationAttributeEditContext


class LocationEditResponseRenderer:
    """
    Handles template rendering and response generation for location editing.
    
    This class encapsulates business logic for:
    - Building template contexts
    - Rendering template fragments for HTMX updates
    - Constructing antinode responses for success/error cases
    """

    def __init__(self) -> None:
        self.form_handler: LocationEditFormHandler = LocationEditFormHandler()

    def build_template_context( self,
                                location                     : Location,
                                location_form                : LocationForm,
                                file_attributes              : QuerySet[LocationAttribute],
                                regular_attributes_formset   : LocationAttributeRegularFormSet,
                                success_message              : Optional[str] = None,
                                error_message                : Optional[str] = None,
                                has_errors                   : bool = False ) -> Dict[str, Any]:
        """Build context dictionary for template rendering.
        
        Args:
            location: Location instance
            location_form: LocationForm instance
            file_attributes: QuerySet of file attributes
            regular_attributes_formset: LocationAttributeRegularFormSet instance
            success_message: Optional success message for display
            error_message: Optional error message for display
            has_errors: Boolean indicating if forms have errors
            
        Returns:
            dict: Template context with all required variables
        """
        non_field_errors = self.form_handler.collect_form_errors(location_form, regular_attributes_formset)
        
        # Create the attribute edit context for template generalization
        attr_context = LocationAttributeEditContext(location)
        
        # Build context with both old and new patterns for compatibility
        context = {
            'location': location,
            'location_form': location_form,
            'owner_form': location_form,  # Generic alias for templates
            'file_attributes': file_attributes,
            'regular_attributes_formset': regular_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_field_errors': non_field_errors,
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        return context

    def render_update_fragments( self,
                                 request                     : HttpRequest,
                                 location                    : Location,
                                 location_form               : Optional[LocationForm] = None,
                                 regular_attributes_formset  : Optional[LocationAttributeRegularFormSet] = None,
                                 success_message             : Optional[str] = None,
                                 error_message               : Optional[str] = None,
                                 has_errors                  : bool = False ) -> Tuple[str, str]:
        """Render both content body and upload form fragments for antinode updates.
        
        This is the main method for generating fragment updates after form submissions.
        
        Args:
            request: HTTP request object
            location: Location instance
            location_form: Optional location form (creates fresh if None)
            regular_attributes_formset: Optional formset (creates fresh if None)
            success_message: Success message for display
            error_message: Error message for display
            has_errors: Boolean indicating if forms have errors
            
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # If forms not provided, create fresh ones (for success case)
        if location_form is None or regular_attributes_formset is None:
            fresh_location_form, file_attributes, fresh_property_formset = self.form_handler.create_location_forms(location)
            if location_form is None:
                location_form = fresh_location_form
            if regular_attributes_formset is None:
                regular_attributes_formset = fresh_property_formset
        else:
            # Forms provided, we still need file_attributes
            _, file_attributes, _ = self.form_handler.create_location_forms(location)
        
        # Build template context
        context: Dict[str, Any] = self.build_template_context(
            location, location_form, file_attributes, regular_attributes_formset,
            success_message, error_message, has_errors
        )
        
        # Render and return fragments
        return self.render_content_fragments(
            request=request,
            context=context,
            location=location,
        )

    def render_content_fragments( self,
                                  request  : HttpRequest,
                                  context  : Dict[str, Any],
                                  location : Location         ) -> Tuple[str, str]:
        """Render both content body and upload form fragments.
        
        Args:
            request: HTTP request object
            context: Template context dictionary
            location: Location instance
            
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # Render both fragments
        content_body: str = render_to_string('location/panes/location_edit_content_body.html', context, request=request)

        # Upload form needs to be specific to location
        file_upload_url: str = reverse('location_attribute_upload',
                                       kwargs={'location_id': location.id})
        
        # Create the attribute edit context for the upload form
        from .location_attribute_edit_context import LocationAttributeEditContext
        attr_context = LocationAttributeEditContext(location)
        
        upload_form: str = render_to_string(
            'attribute/components/upload_form.html',
            {
                'file_upload_url': file_upload_url,
                'attr_context': attr_context
            },
            request=request,  # Needed for context processors (CSRF, DIVID, etc.)
        )
        
        return content_body, upload_form

    def render_success_response( self,
                                 request  : HttpRequest,
                                 location : Location      ) -> HttpResponse:
        """Render success response using custom JSON format - multiple target replacement.
        
        Args:
            request: HTTP request object
            location: Location instance
            
        Returns:
            HttpResponse: Success response with JSON format for custom Ajax handling
        """
        # Re-render both content body and upload form with fresh forms
        content_body, upload_form = self.render_update_fragments(
            request=request,
            location=location, 
            success_message=DefaultMessages.SAVE_SUCCESS
        )
        
        # Get the edit context to build proper target selectors
        attr_context = LocationAttributeEditContext(location)
        
        # Build response using the new helper
        return (AttributeResponseBuilder()
                .success()
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
                .with_message(DefaultMessages.SAVE_SUCCESS)
                .build_http_response())

    def render_error_response(
            self,
            request                     : HttpRequest,
            location                    : Location,
            location_form               : LocationForm,
            regular_attributes_formset  : LocationAttributeRegularFormSet ) -> HttpResponse:
        """Render error response using custom JSON format - multiple target replacement.
        
        Args:
            request: HTTP request object
            location: Location instance
            location_form: LocationForm instance with validation errors
            regular_attributes_formset: FormSet instance with validation errors
            
        Returns:
            HttpResponse: Error response with JSON format for custom Ajax handling
        """
        # Re-render both content body and upload form with form errors
        content_body, upload_form = self.render_update_fragments(
            request=request,
            location=location, 
            location_form=location_form, 
            regular_attributes_formset=regular_attributes_formset, 
            error_message=DefaultMessages.SAVE_ERROR,
            has_errors=True,
        )
        
        # Get the edit context to build proper target selectors
        attr_context = LocationAttributeEditContext(location)
        
        # Build error response using the new helper
        return (AttributeResponseBuilder()
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
                .build_http_response())

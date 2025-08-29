"""
EntityEditResponseRenderer - Handles template rendering and response generation for entity editing.

This class encapsulates the complex rendering and response logic that was previously
embedded in EntityEditView, following the "keep views simple" design philosophy.
"""
from django.template.loader import render_to_string
from django.urls import reverse

import hi.apps.common.antinode as antinode
from .entity_edit_form_handler import EntityEditFormHandler


class EntityEditResponseRenderer:
    """
    Handles template rendering and response generation for entity editing.
    
    This class encapsulates business logic for:
    - Building template contexts
    - Rendering template fragments for HTMX updates
    - Constructing antinode responses for success/error cases
    """

    def __init__(self):
        self.form_handler = EntityEditFormHandler()

    def build_template_context(self, entity, entity_form, file_attributes, 
                              property_attributes_formset, success_message=None, 
                              error_message=None, has_errors=False):
        """Build context dictionary for template rendering.
        
        Args:
            entity: Entity instance
            entity_form: EntityForm instance
            file_attributes: QuerySet of file attributes
            property_attributes_formset: EntityAttributeRegularFormSet instance
            success_message: Optional success message for display
            error_message: Optional error message for display
            has_errors: Boolean indicating if forms have errors
            
        Returns:
            dict: Template context with all required variables
        """
        non_field_errors = self.form_handler.collect_form_errors(entity_form, property_attributes_formset)
        
        return {
            'entity': entity,
            'entity_form': entity_form,
            'file_attributes': file_attributes,
            'property_attributes_formset': property_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_field_errors': non_field_errors,
        }

    def render_update_fragments(self, request, entity, entity_form=None, 
                              property_attributes_formset=None, success_message=None,
                              error_message=None, has_errors=False):
        """Render both content body and upload form fragments for antinode updates.
        
        This is the main method for generating fragment updates after form submissions.
        
        Args:
            request: HTTP request object
            entity: Entity instance
            entity_form: Optional entity form (creates fresh if None)
            property_attributes_formset: Optional formset (creates fresh if None)
            success_message: Success message for display
            error_message: Error message for display
            has_errors: Boolean indicating if forms have errors
            
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # If forms not provided, create fresh ones (for success case)
        if entity_form is None or property_attributes_formset is None:
            fresh_entity_form, file_attributes, fresh_property_formset = self.form_handler.create_entity_forms(entity)
            if entity_form is None:
                entity_form = fresh_entity_form
            if property_attributes_formset is None:
                property_attributes_formset = fresh_property_formset
        else:
            # Forms provided, we still need file_attributes
            _, file_attributes, _ = self.form_handler.create_entity_forms(entity)
        
        # Build template context
        context = self.build_template_context(
            entity, entity_form, file_attributes, property_attributes_formset,
            success_message, error_message, has_errors
        )
        
        # Render and return fragments
        return self.render_content_fragments(
            request=request,
            context=context,
            entity=entity,
        )

    def render_content_fragments(self, request, context, entity):
        """Render both content body and upload form fragments.
        
        Args:
            request: HTTP request object
            context: Template context dictionary
            entity: Entity instance
            
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # Render both fragments
        content_body = render_to_string('entity/panes/entity_edit_content_body.html', context)

        # Upload form needs to be specific to entity
        file_upload_url = reverse('entity_attribute_upload',
                                 kwargs={'entity_id': entity.id})
        upload_form = render_to_string(
            'attribute/components/v2/upload_form.html',
            {'file_upload_url': file_upload_url},
            request=request,  # Needed for csrf token
        )
        
        return content_body, upload_form

    def render_success_response(self, request, entity):
        """Render success response using antinode helpers - multiple target replacement.
        
        Args:
            request: HTTP request object
            entity: Entity instance
            
        Returns:
            antinode.Response: Success response for HTMX update
        """
        # Re-render both content body and upload form with fresh forms
        content_body, upload_form = self.render_update_fragments(
            request=request,
            entity=entity, 
            success_message="Changes saved successfully"
        )
        
        return antinode.response(
            insert_map={
                'attr-v2-content': content_body,
                'attr-v2-upload-form-container': upload_form
            }
        )

    def render_error_response(self, request, entity, entity_form, property_attributes_formset):
        """Render error response using antinode helpers - multiple target replacement.
        
        Args:
            request: HTTP request object
            entity: Entity instance
            entity_form: EntityForm instance with validation errors
            property_attributes_formset: FormSet instance with validation errors
            
        Returns:
            antinode.Response: Error response for HTMX update with 400 status
        """
        # Re-render both content body and upload form with form errors
        content_body, upload_form = self.render_update_fragments(
            request=request,
            entity=entity, 
            entity_form=entity_form, 
            property_attributes_formset=property_attributes_formset, 
            error_message="Please correct the errors below",
            has_errors=True,
        )
        
        return antinode.response(
            insert_map={
                'attr-v2-content': content_body,
                'attr-v2-upload-form-container': upload_form
            },
            status=400
        )
"""
EntityEditResponseRenderer - Handles template rendering and response generation for entity editing.

This class encapsulates the complex rendering and response logic that was previously
embedded in EntityEditView, following the "keep views simple" design philosophy.
"""
from typing import Any, Dict, Optional, Tuple
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse

import hi.apps.common.antinode as antinode
from hi.constants import DIVID
from .entity_edit_form_handler import EntityEditFormHandler
from .models import Entity, EntityAttribute
from .forms import EntityForm, EntityAttributeRegularFormSet


class EntityEditResponseRenderer:
    """
    Handles template rendering and response generation for entity editing.
    
    This class encapsulates business logic for:
    - Building template contexts
    - Rendering template fragments for HTMX updates
    - Constructing antinode responses for success/error cases
    """

    def __init__(self) -> None:
        self.form_handler: EntityEditFormHandler = EntityEditFormHandler()

    def build_template_context( self,
                                entity                       : Entity,
                                entity_form                  : EntityForm,
                                file_attributes              : QuerySet[EntityAttribute],
                                regular_attributes_formset   : EntityAttributeRegularFormSet,
                                success_message              : Optional[str] = None,
                                error_message                : Optional[str] = None,
                                has_errors                   : bool = False ) -> Dict[str, Any]:
        """Build context dictionary for template rendering.
        
        Args:
            entity: Entity instance
            entity_form: EntityForm instance
            file_attributes: QuerySet of file attributes
            regular_attributes_formset: EntityAttributeRegularFormSet instance
            success_message: Optional success message for display
            error_message: Optional error message for display
            has_errors: Boolean indicating if forms have errors
            
        Returns:
            dict: Template context with all required variables
        """
        non_field_errors = self.form_handler.collect_form_errors(entity_form, regular_attributes_formset)
        
        return {
            'entity': entity,
            'entity_form': entity_form,
            'file_attributes': file_attributes,
            'regular_attributes_formset': regular_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_field_errors': non_field_errors,
        }

    def render_update_fragments( self,
                                 request                     : HttpRequest,
                                 entity                      : Entity,
                                 entity_form                 : Optional[EntityForm] = None,
                                 regular_attributes_formset  : Optional[EntityAttributeRegularFormSet] = None,
                                 success_message             : Optional[str] = None,
                                 error_message               : Optional[str] = None,
                                 has_errors                  : bool = False ) -> Tuple[str, str]:
        """Render both content body and upload form fragments for antinode updates.
        
        This is the main method for generating fragment updates after form submissions.
        
        Args:
            request: HTTP request object
            entity: Entity instance
            entity_form: Optional entity form (creates fresh if None)
            regular_attributes_formset: Optional formset (creates fresh if None)
            success_message: Success message for display
            error_message: Error message for display
            has_errors: Boolean indicating if forms have errors
            
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # If forms not provided, create fresh ones (for success case)
        if entity_form is None or regular_attributes_formset is None:
            fresh_entity_form, file_attributes, fresh_property_formset = self.form_handler.create_entity_forms(entity)
            if entity_form is None:
                entity_form = fresh_entity_form
            if regular_attributes_formset is None:
                regular_attributes_formset = fresh_property_formset
        else:
            # Forms provided, we still need file_attributes
            _, file_attributes, _ = self.form_handler.create_entity_forms(entity)
        
        # Build template context
        context: Dict[str, Any] = self.build_template_context(
            entity, entity_form, file_attributes, regular_attributes_formset,
            success_message, error_message, has_errors
        )
        
        # Render and return fragments
        return self.render_content_fragments(
            request=request,
            context=context,
            entity=entity,
        )

    def render_content_fragments( self,
                                  request : HttpRequest,
                                  context : Dict[str, Any],
                                  entity  : Entity         ) -> Tuple[str, str]:
        """Render both content body and upload form fragments.
        
        Args:
            request: HTTP request object
            context: Template context dictionary
            entity: Entity instance
            
        Returns:
            tuple: (content_body_html, upload_form_html)
        """
        # Render both fragments
        content_body: str = render_to_string('entity/panes/entity_edit_content_body.html', context, request=request)

        # Upload form needs to be specific to entity
        file_upload_url: str = reverse('entity_attribute_upload',
                                       kwargs={'entity_id': entity.id})
        upload_form: str = render_to_string(
            'attribute/components/upload_form.html',
            {'file_upload_url': file_upload_url},
            request=request,  # Needed for context processors (CSRF, DIVID, etc.)
        )
        
        return content_body, upload_form

    def render_success_response( self,
                                 request : HttpRequest,
                                 entity  : Entity      ) -> 'antinode.Response':
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
                DIVID['ATTR_V2_CONTENT']: content_body,
                DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER']: upload_form
            }
        )

    def render_error_response(
            self,
            request                     : HttpRequest,
            entity                      : Entity,
            entity_form                 : EntityForm,
            regular_attributes_formset : EntityAttributeRegularFormSet ) -> 'antinode.Response':
        """Render error response using antinode helpers - multiple target replacement.
        
        Args:
            request: HTTP request object
            entity: Entity instance
            entity_form: EntityForm instance with validation errors
            regular_attributes_formset: FormSet instance with validation errors
            
        Returns:
            antinode.Response: Error response for HTMX update with 400 status
        """
        # Re-render both content body and upload form with form errors
        content_body, upload_form = self.render_update_fragments(
            request=request,
            entity=entity, 
            entity_form=entity_form, 
            regular_attributes_formset=regular_attributes_formset, 
            error_message="Please correct the errors below",
            has_errors=True,
        )
        
        return antinode.response(
            insert_map={
                DIVID['ATTR_V2_CONTENT']: content_body,
                DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER']: upload_form
            },
            status=400
        )
    

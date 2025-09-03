import logging
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse

from .edit_context import AttributeEditContext
from .edit_form_handler import AttributeEditFormHandler
from .edit_response_renderer import AttributeEditResponseRenderer

logger = logging.getLogger(__name__)


class AttributeEditViewMixin:

    def post_attribute_form( self,
                             request       : HttpRequest,
                             attr_context  : AttributeEditContext ) -> HttpResponse:
    
        # Delegate form handling to specialized handlers
        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        
        edit_form_data = form_handler.create_edit_form_data(
            attr_context = attr_context,
            form_data = request.POST,
        )
        
        if form_handler.validate_forms( edit_form_data = edit_form_data ):
            form_handler.save_forms(
                attr_context = attr_context,
                edit_form_data = edit_form_data,
                request = request,
            )
            return renderer.render_success_response(
                attr_context = attr_context,
                request = request,
            )
        else:
            return renderer.render_error_response(
                attr_context = attr_context,
                edit_form_data = edit_form_data,
                request = request,
            )

    def create_initial_template_context( self, attr_context  : AttributeEditContext ) -> Dict[str, Any]:
        """ 
        Returns:
            dict: Template context for initial form display
        """
        form_handler = AttributeEditFormHandler()
        edit_form_data = form_handler.create_edit_form_data(
            attr_context = attr_context,
        )
        context = {
            'owner_form': edit_form_data.owner_form,
            'file_attributes': edit_form_data.file_attributes,
            'regular_attributes_formset': edit_form_data.regular_attributes_formset,

            # Duplicate with explicit naming for convenience.
            f'{attr_context.owner_type}_form': edit_form_data.owner_form,
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update( attr_context.to_template_context() )
        return context
    
        

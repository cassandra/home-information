import logging
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse

from .edit_context import AttributeItemEditContext
from .edit_form_handler import AttributeEditFormHandler
from .edit_response_renderer import AttributeEditResponseRenderer

logger = logging.getLogger(__name__)


class AttributeEditViewMixin:

    def post_attribute_form( self,
                             request       : HttpRequest,
                             attr_item_context  : AttributeItemEditContext ) -> HttpResponse:
    
        # Delegate form handling to specialized handlers
        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        
        edit_form_data = form_handler.create_edit_form_data(
            attr_item_context = attr_item_context,
            form_data = request.POST,
        )
        
        if form_handler.validate_forms( edit_form_data = edit_form_data ):
            form_handler.save_forms(
                attr_item_context = attr_item_context,
                edit_form_data = edit_form_data,
                request = request,
            )
            return renderer.render_success_response(
                attr_item_context = attr_item_context,
                request = request,
            )
        else:
            return renderer.render_error_response(
                attr_item_context = attr_item_context,
                edit_form_data = edit_form_data,
                request = request,
            )

    def create_initial_template_context( self,
                                         attr_item_context  : AttributeItemEditContext ) -> Dict[str, Any]:
        """ 
        Returns:
            dict: Template context for initial form display
        """
        form_handler = AttributeEditFormHandler()
        edit_form_data = form_handler.create_edit_form_data(
            attr_item_context = attr_item_context,
        )
        context = {
            'owner_form': edit_form_data.owner_form,
            'file_attributes': edit_form_data.file_attributes,
            'regular_attributes_formset': edit_form_data.regular_attributes_formset,

            # Duplicate with explicit naming for convenience.
            f'{attr_item_context.owner_type}_form': edit_form_data.owner_form,
        }
        
        # Merge in the context variables from AttributeItemEditContext
        context.update( attr_item_context.to_template_context() )
        return context
    
        

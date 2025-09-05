import logging
from typing import Any, Dict, List, Optional

from .edit_context import AttributeItemEditContext, AttributePageEditContext
from .edit_form_handler import AttributeEditFormHandler
from .transient_models import AttributeEditFormData, AttributeMultiEditFormData

logger = logging.getLogger(__name__)


class AttributeEditTemplateContextBuilder:

    def __init__(self) -> None:
        self.form_handler = AttributeEditFormHandler()
        return
    
    def build_initial_template_context(
            self,
            attr_item_context  : AttributeItemEditContext ) -> Dict[str, Any]:

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

    def build_response_template_context(
            self,
            attr_item_context  : AttributeItemEditContext,
            edit_form_data     : AttributeEditFormData,
            success_message    : Optional[str]          = None,
            error_message      : Optional[str]          = None,
            has_errors         : bool                   = False ) -> Dict[str, Any]:
        """
        Returns:
            dict: Template context with all required variables
        """
        non_form_errors = self.form_handler.collect_form_errors(
            edit_form_data = edit_form_data,
        )
        
        # Build context with both old and new patterns for compatibility
        context = {
            'owner_form': edit_form_data.owner_form,
            'file_attributes': edit_form_data.file_attributes,
            'regular_attributes_formset': edit_form_data.regular_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_form_errors': non_form_errors,
        }
        
        # Merge in the context variables from AttributeItemEditContext
        context.update( attr_item_context.to_template_context() )
        
        return context

    def build_initial_template_context_multi(
            self,
            attr_page_context       : AttributePageEditContext,
            attr_item_context_list  : List[AttributeItemEditContext] ) -> Dict[str, Any]:

        form_handler = AttributeEditFormHandler()
        
        multi_edit_form_data_list = form_handler.create_multi_edit_form_data(
            attr_item_context_list = attr_item_context_list,
        )
        context = {
            'multi_edit_form_data_list': multi_edit_form_data_list,
        }
        # Merge in the context variables from AttributeItemEditContext
        context.update( attr_page_context.to_template_context() )
        return context

    def build_response_template_context_multi(
            self,
            attr_page_context          : AttributePageEditContext,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            success_message            : Optional[str]          = None,
            error_message              : Optional[str]          = None,
            has_errors                 : bool                   = False ) -> Dict[str, Any]:

        non_form_errors = self.form_handler.collect_form_errors_multi(
            multi_edit_form_data_list = multi_edit_form_data_list,
        )        
        context = {
            'multi_edit_form_data_list': multi_edit_form_data_list,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
            'non_form_errors': non_form_errors,
        }
        
        # Merge in the context variables from AttributePageEditContext
        context.update( attr_page_context.to_template_context() )
        
        return context

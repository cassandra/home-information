import logging
from typing import Any, Dict, List

from django.http import HttpRequest, HttpResponse

from hi.views import page_not_found_response

from .edit_context import AttributeItemEditContext, AttributePageEditContext
from .edit_form_handler import AttributeEditFormHandler
from .edit_response_renderer import AttributeEditResponseRenderer
from .models import AttributeModel

logger = logging.getLogger(__name__)


class AttributeEditViewMixin:

    def post_attribute_form( self,
                             request       : HttpRequest,
                             attr_item_context  : AttributeItemEditContext ) -> HttpResponse:
    
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
    
        
class AttributeUploadViewMixin:

    def post_upload( self,
                     request       : HttpRequest,
                     attr_item_context  : AttributeItemEditContext ) -> HttpResponse:

        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()

        attribute_upload_form = form_handler.create_upload_form(
            attr_item_context = attr_item_context,
            request = request,
        )
        if form_handler.validate_upload_form( attribute_upload_form ):
            form_handler.save_upload_form( attribute_upload_form )
            return renderer.render_upload_success_response(
                attr_item_context = attr_item_context,
                attribute_upload_form = attribute_upload_form,
                request = request,
            )
        else:
            return renderer.render_upload_error_response(
                attr_item_context = attr_item_context,
                attribute_upload_form = attribute_upload_form,
                request = request,
            )

        
class AttributeHistoryViewMixin:

    ATTRIBUTE_HISTORY_VIEW_LIMIT = 50

    def get_history( self,
                     request            : HttpRequest,
                     attribute          : AttributeModel,
                     attr_item_context  : AttributeItemEditContext ) -> HttpResponse:

        renderer = AttributeEditResponseRenderer()

        # Get history records for this attribute
        history_model_class = attribute._get_history_model_class()
        if history_model_class:
            history_records = history_model_class.objects.filter(
                attribute = attribute
            ).order_by('-changed_datetime')[:self.ATTRIBUTE_HISTORY_VIEW_LIMIT]  # Limit for inline display
        else:
            history_records = []

        return renderer.render_history_response(
            attr_item_context = attr_item_context,
            attribute = attribute,
            history_records = history_records,
            request= request,
        )


class AttributeRestoreViewMixin:

    def post_restore( self,
                      request            : HttpRequest,
                      attribute          : AttributeModel,
                      history_id         : int,
                      attr_item_context  : AttributeItemEditContext ) -> HttpResponse:

        renderer = AttributeEditResponseRenderer()

        history_model_class = attribute._get_history_model_class()
        if not history_model_class:
            return page_not_found_response(request, "No history available for this attribute type.")
        
        try:
            history_record = history_model_class.objects.get(
                pk=history_id, attribute=attribute
            )
        except history_model_class.DoesNotExist:
            return page_not_found_response( request, "History record not found." )
        
        # Restore the value from the history record
        attribute.value = history_record.value
        attribute.save()  # This will create a new history record

        return renderer.render_success_response(
            attr_item_context = attr_item_context,
            request= request,
        )


class AttributeMultiEditViewMixin:
    
    def post_attribute_form(
            self,
            request                 : HttpRequest,
            attr_page_context       : AttributePageEditContext,
            attr_item_context_list  : List[AttributeItemEditContext] ) -> HttpResponse:
    
        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()    

        multi_edit_form_data_list = form_handler.create_multi_edit_form_data(
            attr_item_context_list = attr_item_context_list,
        )
        
        if form_handler.validate_forms_multi( multi_edit_form_data_list = multi_edit_form_data_list ):
            form_handler.save_forms_multi(
                multi_edit_form_data_list = multi_edit_form_data_list,
                request = request,
            )
            return renderer.render_success_response_multi(
                attr_page_context = attr_page_context,
                multi_edit_form_data_list = multi_edit_form_data_list,
                request = request,
            )
        else:
            return renderer.render_error_response_multi(
                attr_page_context = attr_page_context,
                multi_edit_form_data_list = multi_edit_form_data_list,
                request = request,
            )


    def create_initial_template_context(
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
        

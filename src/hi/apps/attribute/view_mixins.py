import logging
from typing import Any, Dict, List

from django.http import HttpRequest, HttpResponse


from .edit_context import AttributeItemEditContext, AttributePageEditContext
from .edit_form_handler import AttributeEditFormHandler
from .edit_response_renderer import AttributeEditResponseRenderer
from .edit_template_context_builder import AttributeEditTemplateContextBuilder
from .models import AttributeModel

logger = logging.getLogger(__name__)


class AttributeEditCommonMixin:
    """ Common mixins are those where we only deal with a single attribuet at a time.
    Thus, it does not depend if we are using a single item or mutliple item views.
    """

    ATTRIBUTE_HISTORY_VIEW_LIMIT = 50
    
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

    def do_restore( self,
                    attribute          : AttributeModel,
                    history_id         : int ):
        """ Caller should catch exceptions """
        
        history_model_class = attribute._get_history_model_class()
        if not history_model_class:
            raise NotImplementedError("No history available for this attribute type.")

        # May raise: history_model_class.DoesNotExist
        history_record = history_model_class.objects.get(
            pk = history_id,
            attribute = attribute
        )

        attribute.value = history_record.value
        attribute.save()  # This will create a new history record too
        return

    
class AttributeEditViewMixin( AttributeEditCommonMixin ):

    def post_attribute_form( self,
                             request       : HttpRequest,
                             attr_item_context  : AttributeItemEditContext ) -> HttpResponse:
    
        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        
        edit_form_data = form_handler.create_edit_form_data(
            attr_item_context = attr_item_context,
            form_data = request.POST,
        )
        
        forms_valid = form_handler.validate_forms( edit_form_data = edit_form_data )
        
        if forms_valid:
            self.validate_attributes_extra(
                attr_item_context = attr_item_context,
                regular_attributes_formset = edit_form_data.regular_attributes_formset,
                request = request,
            )
            # Re-check formset validity after extra validation
            forms_valid = edit_form_data.regular_attributes_formset.is_valid()
        
        if forms_valid:
            form_handler.save_forms(
                attr_item_context = attr_item_context,
                edit_form_data = edit_form_data,
                request = request,
            )
            return renderer.render_form_success_response(
                attr_item_context = attr_item_context,
                request = request,
                message = None,  # Use default message
            )
        else:
            return renderer.render_form_error_response(
                attr_item_context = attr_item_context,
                edit_form_data = edit_form_data,
                request = request,
            )
        return

    def validate_attributes_extra(self, attr_item_context, regular_attributes_formset, request):
        """Optional extra validation hook called after forms are valid but before saving."""
        pass

    def create_initial_template_context(
            self,
            attr_item_context  : AttributeItemEditContext ) -> Dict[str, Any]:

        template_context_builder = AttributeEditTemplateContextBuilder()
        return template_context_builder.build_initial_template_context(
            attr_item_context = attr_item_context,
        )

    def post_restore( self,
                      request            : HttpRequest,
                      attribute          : AttributeModel,
                      history_id         : int,
                      attr_item_context  : AttributeItemEditContext ) -> HttpResponse:

        renderer = AttributeEditResponseRenderer()

        try:
            self.do_restore(
                attribute = attribute,
                history_id = history_id,
            )
            return renderer.render_restore_success_response(
                attr_item_context = attr_item_context,
                request = request,
            )
        except Exception as e:
            return renderer.render_restore_error_response( str(e) )
        

class AttributeMultiEditViewMixin( AttributeEditCommonMixin ):
    
    def post_attribute_form(
            self,
            request                 : HttpRequest,
            attr_page_context       : AttributePageEditContext,
            attr_item_context_list  : List[AttributeItemEditContext] ) -> HttpResponse:
        
        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()    
        
        multi_edit_form_data_list = form_handler.create_multi_edit_form_data(
            attr_item_context_list = attr_item_context_list,
            form_data = request.POST,
        )
        
        if form_handler.validate_forms_multi( multi_edit_form_data_list = multi_edit_form_data_list ):
            form_handler.save_forms_multi(
                multi_edit_form_data_list = multi_edit_form_data_list,
                request = request,
            )
            return renderer.render_form_success_response_multi(
                attr_page_context = attr_page_context,
                multi_edit_form_data_list = multi_edit_form_data_list,
                request = request,
                message = None,  # Use default message
            )
        else:
            return renderer.render_form_error_response_multi(
                attr_page_context = attr_page_context,
                multi_edit_form_data_list = multi_edit_form_data_list,
                request = request,
            )
        
    def create_initial_template_context(
            self,
            attr_page_context       : AttributePageEditContext,
            attr_item_context_list  : List[AttributeItemEditContext] ) -> Dict[str, Any]:

        template_context_builder = AttributeEditTemplateContextBuilder()
        return template_context_builder.build_initial_template_context_multi(
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )

    def post_restore( self,
                      request                 : HttpRequest,
                      attribute               : AttributeModel,
                      history_id              : int,
                      attr_page_context       : AttributePageEditContext,
                      attr_item_context_list  : List[AttributeItemEditContext] ) -> HttpResponse:

        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()    

        try:
            self.do_restore(
                attribute = attribute,
                history_id = history_id,
            )
        except Exception as e:
            return renderer.render_restore_error_response( str(e) )
        
        multi_edit_form_data_list = form_handler.create_multi_edit_form_data(
            attr_item_context_list = attr_item_context_list,
        )
        return renderer.render_restore_success_response_multi(
            attr_page_context = attr_page_context,
            multi_edit_form_data_list = multi_edit_form_data_list,
            request = request,
        )
    

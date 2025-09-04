import logging
from typing import List, Optional

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

from .edit_context import AttributeItemEditContext, AttributePageEditContext
from .edit_form_handler import AttributeEditFormHandler
from .edit_template_context_builder import AttributeEditTemplateContextBuilder
from .forms import AttributeUploadForm
from .models import AttributeModel, AttributeValueHistoryModel
from .response_helpers import AttributeResponseBuilder, UpdateMode
from .response_constants import DefaultMessages
from .transient_models import AttributeEditFormData, AttributeMultiEditFormData

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
        self.template_context_builder = AttributeEditTemplateContextBuilder()
        return
    
    def render_form_success_response(
            self,
            attr_item_context  : AttributeItemEditContext,
            request            : HttpRequest,
            message            : DefaultMessages.SAVE_SUCCESS ) -> HttpResponse:
        """Render success response using custom JSON format - multiple target replacement.
        Returns:
            HttpResponse: Success response with JSON format for custom Ajax handling
        """
        # Re-render both content body and upload form with fresh forms
        content_body = self.render_update_content_body(
            attr_item_context = attr_item_context, 
            request = request,
            success_message = DefaultMessages.SAVE_SUCCESS
        )
        response_builder = (
            AttributeResponseBuilder()
            .success()
            .add_update(
                target = f"#{attr_item_context.content_html_id}",
                html = content_body,
                mode = UpdateMode.REPLACE
            )
        )
        if attr_item_context.uses_file_uploads:
            upload_form = self.render_upload_form(
                attr_item_context = attr_item_context, 
                request = request,
            )
            response_builder.add_update(
                target = f"#{attr_item_context.upload_form_container_html_id}",
                html = upload_form,
                mode = UpdateMode.REPLACE
            )
            
        return (
            response_builder
            .with_message(message)
            .build_http_response()
        )

    def render_form_error_response(
            self,
            attr_item_context  : AttributeItemEditContext,
            edit_form_data     : AttributeEditFormData,
            request            : HttpRequest           ) -> HttpResponse:
        """Render error response using custom JSON format - multiple target replacement.
        Returns:
            HttpResponse: Error response with JSON format for custom Ajax handling
        """
        # Re-render both content body and upload form with form errors
        content_body = self.render_update_content_body(
            attr_item_context = attr_item_context, 
            request = request,
            edit_form_data = edit_form_data,
            error_message = DefaultMessages.SAVE_ERROR,
            has_errors = True,
        )
        response_builder = (
            AttributeResponseBuilder()
            .error()
            .add_update(
                target = f"#{attr_item_context.content_html_id}",
                html = content_body,
                mode = UpdateMode.REPLACE
            )
        )
        if attr_item_context.uses_file_uploads:
            upload_form = self.render_upload_form(
                attr_item_context = attr_item_context, 
                request = request,
            )
            response_builder.add_update(
                target = f"#{attr_item_context.upload_form_container_html_id}",
                html = upload_form,
                mode = UpdateMode.REPLACE
            )

        return (
            response_builder
            .with_message(DefaultMessages.SAVE_ERROR)
            .build_http_response()
        )

    def render_update_content_body(
            self,
            attr_item_context  : AttributeItemEditContext,
            request            : HttpRequest,
            edit_form_data     : AttributeEditFormData  = None,
            success_message    : Optional[str]          = None,
            error_message      : Optional[str]          = None,
            has_errors         : bool                   = False ) -> str:

        # If forms not provided, create fresh ones (for success case)
        updated_form_data = self.get_updated_form_data(
            attr_item_context = attr_item_context,
            edit_form_data = edit_form_data,
        )
        template_context = self.template_context_builder.build_response_template_context(
            attr_item_context = attr_item_context,
            edit_form_data = updated_form_data,
            success_message = success_message,
            error_message = error_message,
            has_errors= has_errors,
        )
        return render_to_string(
            attr_item_context.content_body_template_name,
            template_context,
            request = request,  # Needed for context processors (CSRF, DIVID, etc.)
        )

    def get_updated_form_data(
            self,
            attr_item_context  : AttributeItemEditContext,
            edit_form_data     : AttributeEditFormData  = None ) -> str:

        fresh_form_data = self.form_handler.create_edit_form_data(
            attr_item_context= attr_item_context,
        )
        if not edit_form_data:
            return fresh_form_data
        
        if edit_form_data.owner_form is None:
            edit_form_data.owner_form = fresh_form_data.owner_form
        if edit_form_data.regular_attributes_formset is None:
            edit_form_data.regular_attributes_formset = fresh_form_data.regular_attributes_formset
        if edit_form_data.file_attributes is None:
            edit_form_data.file_attributes = fresh_form_data.file_attributes
        return edit_form_data
        
    def render_upload_form(
            self,
            attr_item_context  : AttributeItemEditContext,
            request            : HttpRequest ) -> str:
        assert attr_item_context.uses_file_uploads

        return render_to_string(
            'attribute/components/upload_form.html',
            {
                'file_upload_url': attr_item_context.file_upload_url,
                'attr_item_context': attr_item_context
            },
            request = request,  # Needed for context processors (CSRF, DIVID, etc.)
        )
    
    def render_upload_success_response(
            self,
            attr_item_context      : AttributeItemEditContext,
            attribute_upload_form  : AttributeUploadForm,
            request                : HttpRequest      ) -> HttpResponse:

        context = {'attribute': attribute_upload_form.instance }
        context.update( attr_item_context.to_template_context() )

        file_card_html = render_to_string(
            'attribute/components/file_card.html',
            context,
            request = request,
        )
        return (
            AttributeResponseBuilder()
            .success()
            .add_update(
                target = f"#{attr_item_context.file_grid_html_id}",
                html = file_card_html,
                mode = UpdateMode.APPEND,
            )
            .with_message(DefaultMessages.UPLOAD_SUCCESS)
            .build_http_response()
        )
        
    def render_upload_error_response( self,
                                      attr_item_context      : AttributeItemEditContext,
                                      attribute_upload_form  : AttributeUploadForm,
                                      request                : HttpRequest           ) -> HttpResponse:
        error_html: str = render_to_string(
            'attribute/components/status_message.html',
            {
                'error_message': DefaultMessages.UPLOAD_ERROR,
                'form_errors': attribute_upload_form.errors,
            }
        )
        return (
            AttributeResponseBuilder()
            .error()
            .add_update(
                target=f'#{attr_item_context.status_msg_html_id}',
                html=error_html,
                mode=UpdateMode.REPLACE
            )
            .with_message(DefaultMessages.UPLOAD_ERROR)
            .build_http_response()
        )

    def render_history_response( self,
                                 attr_item_context  : AttributeItemEditContext,
                                 attribute          : AttributeModel,
                                 history_records    : List[AttributeValueHistoryModel],
                                 request            : HttpRequest           ) -> HttpResponse:
        context = {
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': attr_item_context.history_url_name,
            'restore_url_name': attr_item_context.restore_url_name,
        }
        context.update(attr_item_context.to_template_context())

        html_content = render_to_string(
            template_name = 'attribute/components/attribute_history_inline.html', 
            context = context, 
            request = request
        )
        
        # Build JSON response with target selector for history content
        return (
            AttributeResponseBuilder()
            .success()
            .add_update(
                target=f"#{attr_item_context.history_target_id(attribute.id)}",
                html=html_content,
                mode=UpdateMode.REPLACE
            )
            .with_message(f"History for {attribute.name}")
            .build_http_response()
        )

    def render_restore_success_response(
            self,
            attr_item_context  : AttributeItemEditContext,
            request            : HttpRequest ) -> HttpResponse:

        return self.render_form_success_response(
            attr_item_context = attr_item_context,
            request = request,
            message = DefaultMessages.RESTORE_SUCCESS,
        )
    
    def render_restore_error_response( self, message : str ) -> HttpResponse:
        return (
            AttributeResponseBuilder()
            .error()
            .with_message(DefaultMessages.RESTORE_ERROR)
            .build_http_response()
        )
    
    def render_form_success_response_multi(
            self,
            attr_page_context          : AttributePageEditContext,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            request                    : HttpRequest,
            message                    : DefaultMessages.SAVE_SUCCESS ) -> HttpResponse:

        content_body = self.render_update_content_body_multi(
            attr_page_context = attr_page_context,
            multi_edit_form_data_list = multi_edit_form_data_list,
            request = request,
            success_message = DefaultMessages.SAVE_SUCCESS
        )
        response_builder = (
            AttributeResponseBuilder()
            .success()
            .add_update(
                target = f"#{attr_page_context.content_html_id}",
                html = content_body,
                mode = UpdateMode.REPLACE,
            )
        )
        self.build_upload_forms_multi(
            response_builder = response_builder,
            multi_edit_form_data_list = multi_edit_form_data_list,
            request = request,
        )
        return (
            response_builder
            .with_message( message )
            .build_http_response()
        )
        
    def render_form_error_response_multi( 
            self,
            attr_page_context          : AttributePageEditContext,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            request                    : HttpRequest ) -> HttpResponse:

        content_body = self.render_update_content_body_multi(
            attr_page_context = attr_page_context,
            multi_edit_form_data_list = multi_edit_form_data_list,
            request = request,
            error_message = DefaultMessages.SAVE_ERROR,
            has_errors = True,
        )
        response_builder = (
            AttributeResponseBuilder()
            .error()
            .add_update(
                target = f"#{attr_page_context.content_html_id}",
                html = content_body,
                mode = UpdateMode.REPLACE
            )
        )
        self.build_upload_forms_multi(
            response_builder = response_builder,
            multi_edit_form_data_list = multi_edit_form_data_list,
            request = request,
        )
        return (
            response_builder
            .with_message(DefaultMessages.SAVE_ERROR)
            .build_http_response()
        )

    def render_restore_success_response_multi(
            self,
            attr_page_context          : AttributePageEditContext,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            request                    : HttpRequest ) -> HttpResponse:

        return self.render_form_success_response_multi(
            attr_page_context = attr_page_context,
            multi_edit_form_data_list = multi_edit_form_data_list,
            request = request,
            message = DefaultMessages.RESTORE_SUCCESS,
        )
    
    def build_upload_forms_multi(
            self,
            response_builder           : AttributeResponseBuilder,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            request                    : HttpRequest ) -> HttpResponse:
        
        for multi_edit_form_data in multi_edit_form_data_list:
            attr_item_context = multi_edit_form_data.attr_item_context
            if not attr_item_context.uses_file_uploads:
                continue
            upload_form = self.render_upload_form(
                attr_item_context = attr_item_context, 
                request = request,
            )
            response_builder.add_update(
                target = f"#{attr_item_context.upload_form_container_html_id}",
                html = upload_form,
                mode = UpdateMode.REPLACE,
            )
            continue
        return
    
    def render_update_content_body_multi(
            self,
            attr_page_context          : AttributePageEditContext,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            request                    : HttpRequest,
            success_message            : Optional[str]          = None,
            error_message              : Optional[str]          = None,
            has_errors                 : bool                   = False ) -> HttpResponse:

        for multi_edit_form_data in multi_edit_form_data_list:
            updated_form_data = self.get_updated_form_data(
                attr_item_context = multi_edit_form_data.attr_item_context,
                edit_form_data = multi_edit_form_data.edit_form_data,
            )
            multi_edit_form_data.edit_form_data = updated_form_data
            continue
        
        template_context = self.template_context_builder.build_response_template_context_multi(
            attr_page_context = attr_page_context,
            multi_edit_form_data_list = multi_edit_form_data_list,
            success_message = success_message,
            error_message = error_message,
            has_errors = has_errors,
        )
        return render_to_string(
            attr_page_context.content_body_template_name,
            template_context,
            request = request,  # Needed for context processors (CSRF, DIVID, etc.)
        )
        

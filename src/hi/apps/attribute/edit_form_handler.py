import logging
import random
import re
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.forms.utils import ErrorList
from django.http import HttpRequest

from hi.constants import DIVID
from hi.testing.dev_overrides import DevOverrideManager

from .forms import AttributeUploadForm
from .edit_context import AttributeItemEditContext
from .enums import AttributeValueType
from .models import AttributeModel
from .transient_models import AttributeEditFormData, AttributeMultiEditFormData

logger = logging.getLogger(__name__)


class AttributeEditFormHandler:

    INJECT_TEST_ERRORS = True # For testing UI error display
    
    def create_edit_form_data(
            self,
            attr_item_context  : AttributeItemEditContext,
            form_data          : Optional[ Dict[str, Any] ] = None ) -> AttributeEditFormData:
        """
        Args:
            form_data: POST data for bound forms, None for unbound forms
        """
        owner_form = attr_item_context.create_owner_form( form_data )

        # Get file attributes for display (not a formset, just for template rendering)
        file_attributes: QuerySet[AttributeModel] = attr_item_context.attributes_queryset().filter(
            value_type_str = str( AttributeValueType.FILE )
        ).order_by('id')
        
        # Regular attributes formset (should exclude FILE attributes)
        regular_attributes_formset = attr_item_context.create_regular_attributes_formset(
            form_data = form_data,
        )
        return AttributeEditFormData(
            owner_form = owner_form,
            file_attributes = file_attributes,
            regular_attributes_formset = regular_attributes_formset,
        )

    def validate_forms(self, edit_form_data: AttributeEditFormData) -> bool:
        """
        Returns:
            bool: True if both forms are valid, False otherwise
        """
        if settings.DEBUG and settings.DEBUG_INJECT_ATTRIBUTE_FORM_ERRORS:
            return DevOverrideManager.validate_forms( edit_form_data )
        
        # Normal validation
        if edit_form_data.owner_form and not edit_form_data.owner_form.is_valid():
            return False
        return edit_form_data.regular_attributes_formset.is_valid()
    
    def save_forms( self,
                    attr_item_context   : AttributeItemEditContext,
                    edit_form_data : AttributeEditFormData,
                    request        : HttpRequest ) -> None:

        with transaction.atomic():
            if edit_form_data.owner_form:
                edit_form_data.owner_form.save()
            edit_form_data.regular_attributes_formset.save()
            
            self.process_file_title_updates( 
                attr_item_context = attr_item_context,
                request = request,
            )
            self.process_file_deletions(
                attr_item_context = attr_item_context,
                request = request,
            )
        return
    
    def process_file_deletions( self,
                                attr_item_context  : AttributeItemEditContext,
                                request       : HttpRequest           ) -> None:
        file_deletes: List[str] = request.POST.getlist( DIVID['ATTR_V2_DELETE_FILE_ATTR'] )
        if not file_deletes:
            return

        AttributeModelClass = attr_item_context.attribute_model_subclass
        
        for attr_id in file_deletes:
            if not attr_id:  # Skip empty values
                continue
            try:
                file_attribute = AttributeModelClass.objects.get(
                    id = attr_id, 
                    value_type_str = str(AttributeValueType.FILE)
                )
                # Verify permission to delete
                if file_attribute.attribute_type.can_delete:
                    file_attribute.delete()
            except AttributeModelClass.DoesNotExist:
                pass
            continue
        return
    
    def process_file_title_updates( self,
                                    attr_item_context  : AttributeItemEditContext,
                                    request       : HttpRequest      ) -> None:
        """Process file_title_* fields from POST data to update file attribute values."""
        # Pattern to match file_title_{owner_id}_{attribute_id}
        file_title_pattern = re.compile(r'^file_title_(\d+)_(\d+)$')

        AttributeModelClass = attr_item_context.attribute_model_subclass

        for field_name, new_title in request.POST.items():
            match = file_title_pattern.match(field_name)
            if not match:
                continue
                
            owner_id_str: str
            attribute_id_str: str
            owner_id_str, attribute_id_str = match.groups()
      
            # Validate owner_id matches current owner
            if int(owner_id_str) != attr_item_context.owner.id:
                logger.warning(f'File title field {field_name} has mismatched owner ID')
                continue
            
            try:
                attribute_id: int = int(attribute_id_str)
                attribute = AttributeModelClass.objects.get(
                    id = attribute_id,
                    value_type_str = str(AttributeValueType.FILE)
                )
                # Clean and validate the new title
                new_title = new_title.strip()
                if not new_title:
                    logger.warning(f'Empty title provided for file attribute {attribute_id}')
                    continue
                
                # Check if title actually changed
                if attribute.value != new_title:
                    attribute.value = new_title
                    attribute.save()  # This will also create a history record
                    
            except (ValueError) as e:
                logger.warning(f'Invalid file title field {field_name}: {e}')
            except (AttributeModelClass.DoesNotExist) as e:
                logger.warning(f'File attribute not found {field_name}: {e}')

    def collect_form_errors(self, edit_form_data: AttributeEditFormData) -> List[str]:
        """
        Collect errors for central display and count all form errors (as side efffect).

        Note: Individual form.non_field_errors() are NOT collected in the return list
        They should be displayed inline with the specific forms/fields
        """

        non_form_errors = []
        total_error_count = 0
        
        if edit_form_data.owner_form:
            owner_form = edit_form_data.owner_form
            total_error_count += len( owner_form.non_field_errors() )
            for field_name in owner_form.fields:
                total_error_count += len( owner_form[field_name].errors )
                continue
        
        if edit_form_data.regular_attributes_formset:
            formset = edit_form_data.regular_attributes_formset
            try:
                # Accessing management_form will raise ValidationError if data is missing
                formset.management_form
            except Exception:
                # Management form missing - count as one system error
                total_error_count += 1
                non_form_errors.append(
                    "Form data is missing or incomplete."
                )
            else:
                # Count formset-level errors
                formset_non_form_errors = formset.non_form_errors()
                if formset_non_form_errors:
                    total_error_count += len(formset_non_form_errors)
                    non_form_errors.extend(
                        [f"Properties: {error}" for error in formset_non_form_errors]
                    )
                
                # Count individual form errors (field and non-field)
                for form in formset.forms:
                    # Count field errors for each form using standard API
                    total_error_count += len( form.non_field_errors() )
                    for field_name in form.fields:
                        total_error_count += len( form[field_name].errors )
                        continue
        
        edit_form_data.error_count = total_error_count
        return non_form_errors

    def create_upload_form( self,
                            attr_item_context  : AttributeItemEditContext,
                            request            : HttpRequest ) -> AttributeUploadForm:
        assert attr_item_context.uses_file_uploads

        AttributeUploadFormClass = attr_item_context.attribute_upload_form_class
        owner_attribute = attr_item_context.create_attribute_model()
        return AttributeUploadFormClass(
            request.POST,
            request.FILES,
            instance = owner_attribute,
        )

    def validate_upload_form( self, attribute_upload_form : AttributeUploadForm ) -> bool:
        return attribute_upload_form.is_valid()
    
    def save_upload_form( self, attribute_upload_form : AttributeUploadForm ) -> None:
        with transaction.atomic():
            attribute_upload_form.save()   
        return
    
    def create_multi_edit_form_data(
            self,
            attr_item_context_list  : List[AttributeItemEditContext],
            form_data               : Optional[ Dict[str, Any] ] = None ) -> List[AttributeMultiEditFormData]:

        multi_edit_form_data_list = list()
        for attr_item_context in attr_item_context_list:
            edit_form_data = self.create_edit_form_data(
                attr_item_context = attr_item_context,
                form_data = form_data,
            )
            multi_edit_form_data = AttributeMultiEditFormData(
                attr_item_context = attr_item_context,
                edit_form_data = edit_form_data,
            )
            multi_edit_form_data_list.append( multi_edit_form_data )
            continue
        return multi_edit_form_data_list

    def validate_forms_multi(
            self,
            multi_edit_form_data_list : List[AttributeMultiEditFormData] ) -> bool:

        if settings.DEBUG and settings.DEBUG_INJECT_ATTRIBUTE_FORM_ERRORS:
            for multi_edit_form_data in multi_edit_form_data_list:
                self.validate_forms( edit_form_data = multi_edit_form_data.edit_form_data )
                continue
            return False
        
        for multi_edit_form_data in multi_edit_form_data_list:
            if not self.validate_forms( edit_form_data = multi_edit_form_data.edit_form_data ):
                return False
            continue
        return True

    def save_forms_multi(
            self,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData],
            request                    : HttpRequest ) -> None:
        for multi_edit_form_data in multi_edit_form_data_list:
            self.save_forms(
                attr_item_context = multi_edit_form_data.attr_item_context,
                edit_form_data = multi_edit_form_data.edit_form_data,
                request = request,
            )
            continue
        return True
            
    def collect_form_errors_multi(
            self,
            multi_edit_form_data_list  : List[AttributeMultiEditFormData] ) -> List[str]:

        non_form_errors = list()
        for multi_edit_form_data in multi_edit_form_data_list:
            errors = self.collect_form_errors(
                edit_form_data = multi_edit_form_data.edit_form_data,
            )
            non_form_errors.extend( errors )
            continue

        return non_form_errors

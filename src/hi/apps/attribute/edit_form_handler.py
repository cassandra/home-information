import logging
import re
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest

from hi.constants import DIVID

from .edit_context import AttributeItemEditContext
from .enums import AttributeValueType
from .models import AttributeModel
from .transient_models import AttributeEditFormData

logger = logging.getLogger(__name__)


class AttributeEditFormHandler:

    def create_edit_form_data( self,
                               attr_item_context  : AttributeItemEditContext,
                               form_data     : Optional[ Dict[str, Any] ] = None ) -> AttributeEditFormData:
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

    def validate_forms( self, edit_form_data : AttributeEditFormData ) -> bool:
        """
        Returns:
            bool: True if both forms are valid, False otherwise
        """
        # Owner form is optional
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

    def collect_form_errors( self, edit_form_data : AttributeEditFormData ) -> List[str]:
        """Collect non-field errors from forms for enhanced error messaging.
        Returns:
            list: Formatted error messages with context prefixes
        """
        non_field_errors: List[str] = []
        
        # Owner form non-field errors
        if ( edit_form_data.owner_form
             and hasattr(edit_form_data.owner_form, 'non_field_errors')
             and edit_form_data.owner_form.non_field_errors() ):
            non_field_errors.extend(
                [f"Owner: {error}"
                 for error in edit_form_data.owner_form.non_field_errors()]
            )
        
        # Property formset non-field errors
        if ( edit_form_data.regular_attributes_formset
             and hasattr(edit_form_data.regular_attributes_formset, 'non_field_errors')
             and edit_form_data.regular_attributes_formset.non_field_errors() ):
            non_field_errors.extend(
                [f"Properties: {error}"
                 for error in edit_form_data.regular_attributes_formset.non_field_errors()]
            )
        
        # Individual property form non-field errors
        if edit_form_data.regular_attributes_formset:
            for i, form in enumerate(edit_form_data.regular_attributes_formset.forms):
                if hasattr(form, 'non_field_errors') and form.non_field_errors():
                    property_name: str = form.instance.name if form.instance.pk else f"New Property #{i+1}"
                    non_field_errors.extend([f"{property_name}: {error}"
                                             for error in form.non_field_errors()])
                continue
        
        return non_field_errors

"""
LocationEditFormHandler - Handles form creation, validation, and file processing for location editing.

This class follows the same pattern as EntityEditFormHandler, encapsulating the complex 
form-handling business logic that was previously embedded in LocationEditView, following 
the "keep views simple" design philosophy.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from django.db import transaction
from django.http import HttpRequest
from django.db.models import QuerySet

from hi.apps.attribute.enums import AttributeValueType
from .models import Location, LocationAttribute
from .edit.forms import LocationV2EditForm, LocationAttributeRegularFormSet
from .location_attribute_edit_context import LocationAttributeEditContext

logger = logging.getLogger(__name__)


class LocationEditFormHandler:
    """
    Handles form creation, validation, and file processing for location editing.
    
    This class encapsulates business logic for:
    - Creating and managing location forms and formsets
    - Processing file deletions and title updates  
    - Collecting and formatting form validation errors
    """

    @staticmethod
    def get_formset_prefix(location: Location) -> str:
        """
        Get the formset prefix for regular attributes formset.
        
        This is the single source of truth for formset prefix logic.
        Tests and other code should use this method to ensure consistency.
        
        Args:
            location: Location instance
            
        Returns:
            str: The prefix to use for the regular attributes formset
        """
        return f'location-{location.id}'

    def create_location_forms(
            self,
            location  : Location,
            form_data : Optional[Dict[str, Any]] = None
    ) -> Tuple[LocationV2EditForm, QuerySet[LocationAttribute], LocationAttributeRegularFormSet]:
        """Create location forms used by both initial rendering and fragment updates.
        
        Args:
            location: Location instance
            form_data: POST data for bound forms, None for unbound forms
            
        Returns:
            tuple: (location_form, file_attributes, regular_attributes_formset)
        """
        # Create location form (only name field for this modal)
        location_form: LocationV2EditForm = LocationV2EditForm(form_data, instance=location)
        
        # Get file attributes for display (not a formset, just for template rendering)
        file_attributes: QuerySet[LocationAttribute] = location.attributes.filter(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id')
        
        # Regular attributes formset (automatically excludes FILE attributes)
        regular_attributes_formset: LocationAttributeRegularFormSet = LocationAttributeRegularFormSet(
            form_data,
            instance=location,
            prefix=self.get_formset_prefix(location),
            form_kwargs={
                'show_as_editable': True,
            }
        )
        
        return location_form, file_attributes, regular_attributes_formset

    def validate_forms( self,
                        location_form              : LocationV2EditForm,
                        regular_attributes_formset : LocationAttributeRegularFormSet ) -> bool:
        """
        Validate location form and property attributes formset.
        
        Args:
            location_form: LocationV2EditForm instance
            regular_attributes_formset: LocationAttributeRegularFormSet instance
            
        Returns:
            bool: True if both forms are valid, False otherwise
        """
        return location_form.is_valid() and regular_attributes_formset.is_valid()

    def save_forms( self,
                    location_form               : LocationV2EditForm,
                    regular_attributes_formset  : LocationAttributeRegularFormSet,
                    request                     : HttpRequest,
                    location                    : Location ) -> None:
        """
        Save forms and process file operations within a transaction.
        
        Args:
            location_form: LocationV2EditForm instance
            regular_attributes_formset: LocationAttributeRegularFormSet instance
            request: HTTP request object
            location: Location instance
        """
        with transaction.atomic():
            location_form.save()
            regular_attributes_formset.save()
            
            # Process file deletions
            self.process_file_deletions(request, location)
            
            # Process file title updates
            self.process_file_title_updates(request, location)

    def process_file_deletions( self,
                                request  : HttpRequest,
                                location : Location      ) -> None:
        """Process file deletion requests from POST data."""
        file_deletes: List[str] = request.POST.getlist('delete_file_attribute')
        if file_deletes:
            for attr_id in file_deletes:
                if attr_id:  # Skip empty values
                    try:
                        file_attribute: LocationAttribute = LocationAttribute.objects.get(
                            id=attr_id, 
                            location=location,
                            value_type_str=str(AttributeValueType.FILE)
                        )
                        # Verify permission to delete
                        if file_attribute.attribute_type.can_delete:
                            file_attribute.delete()
                    except LocationAttribute.DoesNotExist:
                        pass

    def process_file_title_updates( self,
                                    request  : HttpRequest,
                                    location : Location      ) -> None:
        """Process file_title_* fields from POST data to update file attribute values."""
        # Pattern to match file_title_{location_id}_{attribute_id}
        file_title_pattern = re.compile(r'^file_title_(\d+)_(\d+)$')
        
        for field_name, new_title in request.POST.items():
            match = file_title_pattern.match(field_name)
            if not match:
                continue
                
            location_id_str: str
            attribute_id_str: str
            location_id_str, attribute_id_str = match.groups()
            
            # Validate location_id matches current location
            if int(location_id_str) != location.id:
                logger.warning(f'File title field {field_name} has mismatched location ID')
                continue
            
            try:
                attribute_id: int = int(attribute_id_str)
                attribute: LocationAttribute = LocationAttribute.objects.get(
                    pk=attribute_id,
                    location=location,
                    value_type_str=str(AttributeValueType.FILE)
                )
                
                # Clean and validate the new title
                new_title = new_title.strip()
                if not new_title:
                    logger.warning(f'Empty title provided for file attribute {attribute_id}')
                    continue
                
                # Check if title actually changed
                if attribute.value != new_title:
                    attribute.value = new_title
                    attribute.save()  # This will create a history record
                    
            except (ValueError, LocationAttribute.DoesNotExist) as e:
                logger.warning(f'Invalid file title field {field_name}: {e}')

    def collect_form_errors( self,
                             location_form              : LocationV2EditForm,
                             regular_attributes_formset : LocationAttributeRegularFormSet ) -> List[str]:
        """Collect non-field errors from forms for enhanced error messaging.
        
        Args:
            location_form: LocationV2EditForm instance 
            regular_attributes_formset: LocationAttributeRegularFormSet instance
            
        Returns:
            list: Formatted error messages with context prefixes
        """
        non_field_errors: List[str] = []
        
        # Location form non-field errors
        if ( location_form
             and hasattr(location_form, 'non_field_errors')
             and location_form.non_field_errors() ):
            non_field_errors.extend([f"Location: {error}"
                                     for error in location_form.non_field_errors()])
        
        # Property formset non-field errors
        if ( regular_attributes_formset
             and hasattr(regular_attributes_formset, 'non_field_errors')
             and regular_attributes_formset.non_field_errors() ):
            non_field_errors.extend( [f"Properties: {error}"
                                      for error in regular_attributes_formset.non_field_errors()])
        
        # Individual property form non-field errors
        if regular_attributes_formset:
            for i, form in enumerate(regular_attributes_formset.forms):
                if hasattr(form, 'non_field_errors') and form.non_field_errors():
                    property_name: str = form.instance.name if form.instance.pk else f"New Property #{i+1}"
                    non_field_errors.extend([f"{property_name}: {error}"
                                             for error in form.non_field_errors()])
        
        return non_field_errors

    def create_initial_context( self,
                                location : Location ) -> Dict[str, Any]:
        """Create initial template context for location editing form.
        
        Args:
            location: Location instance
            
        Returns:
            dict: Template context for initial form display
        """
        location_form, file_attributes, regular_attributes_formset = self.create_location_forms(location)
        
        # Create the attribute edit context for template generalization
        attr_context = LocationAttributeEditContext(location)
        
        # Build context with both old and new patterns for compatibility
        context = {
            'location': location,
            'location_form': location_form,
            'owner_form': location_form,  # Generic alias for templates
            'file_attributes': file_attributes,
            'regular_attributes_formset': regular_attributes_formset,
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        return context

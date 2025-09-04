"""
EntityEditFormHandler - Handles form creation, validation, and file processing for entity editing.

This class encapsulates the complex form-handling business logic that was previously
embedded in EntityEditView, following the "keep views simple" design philosophy.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from django.db import transaction
from django.http import HttpRequest
from django.db.models import QuerySet

from hi.apps.attribute.enums import AttributeValueType
from .models import Entity, EntityAttribute
from .forms import EntityForm, EntityAttributeRegularFormSet
from .entity_attribute_edit_context import EntityAttributeItemEditContext

logger = logging.getLogger(__name__)


class EntityEditFormHandler:
    """
    Handles form creation, validation, and file processing for entity editing.
    
    This class encapsulates business logic for:
    - Creating and managing entity forms and formsets
    - Processing file deletions and title updates
    - Collecting and formatting form validation errors
    """

    @staticmethod
    def get_formset_prefix(entity: Entity) -> str:
        """
        Get the formset prefix for regular attributes formset.
        
        This is the single source of truth for formset prefix logic.
        Tests and other code should use this method to ensure consistency.
        
        Args:
            entity: Entity instance
            
        Returns:
            str: The prefix to use for the regular attributes formset
        """
        return f'entity-{entity.id}'

    def create_entity_forms(
            self,
            entity    : Entity,
            form_data : Optional[Dict[str, Any]] = None
    ) -> Tuple[EntityForm, QuerySet[EntityAttribute], EntityAttributeRegularFormSet]:
        """Create entity forms used by both initial rendering and fragment updates.
        
        Args:
            entity: Entity instance
            form_data: POST data for bound forms, None for unbound forms
            
        Returns:
            tuple: (entity_form, file_attributes, regular_attributes_formset)
        """
        # Create entity form
        entity_form: EntityForm = EntityForm(form_data, instance=entity)
        
        # Get file attributes for display (not a formset, just for template rendering)
        file_attributes: QuerySet[EntityAttribute] = entity.attributes.filter(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id')
        
        # Regular attributes formset (automatically excludes FILE attributes)
        regular_attributes_formset: EntityAttributeRegularFormSet = EntityAttributeRegularFormSet(
            form_data,
            instance=entity,
            prefix=self.get_formset_prefix(entity)
        )
        
        return entity_form, file_attributes, regular_attributes_formset

    def validate_forms( self,
                        entity_form                   : EntityForm,
                        regular_attributes_formset    : EntityAttributeRegularFormSet ) -> bool:
        """
        Validate entity form and property attributes formset.
        
        Args:
            entity_form: EntityForm instance
            regular_attributes_formset: EntityAttributeRegularFormSet instance
            
        Returns:
            bool: True if both forms are valid, False otherwise
        """
        return entity_form.is_valid() and regular_attributes_formset.is_valid()

    def save_forms( self,
                    entity_form                  : EntityForm,
                    regular_attributes_formset   : EntityAttributeRegularFormSet,
                    request                      : HttpRequest,
                    entity                       : Entity ) -> None:
        """
        Save forms and process file operations within a transaction.
        
        Args:
            entity_form: EntityForm instance
            regular_attributes_formset: EntityAttributeRegularFormSet instance
            request: HTTP request object
            entity: Entity instance
        """
        with transaction.atomic():
            entity_form.save()
            regular_attributes_formset.save()
            
            # Process file deletions
            self.process_file_deletions(request, entity)
            
            # Process file title updates
            self.process_file_title_updates(request, entity)

    def process_file_deletions( self,
                                request : HttpRequest,
                                entity  : Entity      ) -> None:
        """Process file deletion requests from POST data."""
        file_deletes: List[str] = request.POST.getlist('delete_file_attribute')
        if file_deletes:
            for attr_id in file_deletes:
                if attr_id:  # Skip empty values
                    try:
                        file_attribute: EntityAttribute = EntityAttribute.objects.get(
                            id=attr_id, 
                            entity=entity,
                            value_type_str=str(AttributeValueType.FILE)
                        )
                        # Verify permission to delete
                        if file_attribute.attribute_type.can_delete:
                            file_attribute.delete()
                    except EntityAttribute.DoesNotExist:
                        pass

    def process_file_title_updates( self,
                                    request : HttpRequest,
                                    entity  : Entity      ) -> None:
        """Process file_title_* fields from POST data to update file attribute values."""
        # Pattern to match file_title_{entity_id}_{attribute_id}
        file_title_pattern = re.compile(r'^file_title_(\d+)_(\d+)$')
        
        for field_name, new_title in request.POST.items():
            match = file_title_pattern.match(field_name)
            if not match:
                continue
                
            entity_id_str: str
            attribute_id_str: str
            entity_id_str, attribute_id_str = match.groups()
            
            # Validate entity_id matches current entity
            if int(entity_id_str) != entity.id:
                logger.warning(f'File title field {field_name} has mismatched entity ID')
                continue
            
            try:
                attribute_id: int = int(attribute_id_str)
                attribute: EntityAttribute = EntityAttribute.objects.get(
                    pk=attribute_id,
                    entity=entity,
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
                    
            except (ValueError, EntityAttribute.DoesNotExist) as e:
                logger.warning(f'Invalid file title field {field_name}: {e}')

    def collect_form_errors( self,
                             entity_form                  : EntityForm,
                             regular_attributes_formset   : EntityAttributeRegularFormSet ) -> List[str]:
        """Collect non-field errors from forms for enhanced error messaging.
        
        Args:
            entity_form: EntityForm instance 
            regular_attributes_formset: EntityAttributeRegularFormSet instance
            
        Returns:
            list: Formatted error messages with context prefixes
        """
        non_field_errors: List[str] = []
        
        # Entity form non-field errors
        if ( entity_form
             and hasattr(entity_form, 'non_field_errors')
             and entity_form.non_field_errors() ):
            non_field_errors.extend([f"Entity: {error}"
                                     for error in entity_form.non_field_errors()])
        
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
                                entity : Entity ) -> Dict[str, Any]:
        """Create initial template context for entity editing form.
        
        Args:
            entity: Entity instance
            
        Returns:
            dict: Template context for initial form display
        """
        entity_form, file_attributes, regular_attributes_formset = self.create_entity_forms(entity)
        
        # Create the attribute edit context for template generalization
        attr_item_context = EntityAttributeItemEditContext(entity)
        
        # Build context with both old and new patterns for compatibility
        context = {
            'entity': entity,
            'entity_form': entity_form,
            'owner_form': entity_form,  # Generic alias for templates
            'file_attributes': file_attributes,
            'regular_attributes_formset': regular_attributes_formset,
        }
        
        # Merge in the context variables from AttributeItemEditContext
        context.update(attr_item_context.to_template_context())
        
        return context

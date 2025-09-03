"""
ConfigEditFormHandler - Handles form creation, validation, and processing for config settings editing.
Adapted from Entity/Location patterns for multiple subsystem formsets.
"""
import logging
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.http import HttpRequest

from .forms import SubsystemAttributeFormSet
from .settings_mixins import SettingsMixin
from .subsystem_attribute_edit_context import SubsystemAttributeEditContext
from .subsystem_attribute_edit_data import SubsystemAttributeEditData

logger = logging.getLogger(__name__)


class ConfigEditFormHandler:
    """Handles form creation, validation, and processing for config settings editing."""

    def __init__(self):
        self.settings_mixin = SettingsMixin()

    def create_config_forms(
            self,
            form_data: Optional[Dict[str, Any]] = None,
            files_data: Optional[Dict[str, Any]] = None
    ) -> List[SubsystemAttributeFormSet]:
        """Create formsets for all subsystems used by both initial rendering and fragment updates."""
        
        subsystem_list = self.settings_mixin.settings_manager().get_subsystems()
        subsystem_formset_list = []
        
        for subsystem in subsystem_list:
            subsystem_formset = SubsystemAttributeFormSet(
                form_data,
                files_data,
                instance=subsystem,
                prefix=f'subsystem-{subsystem.id}',
                form_kwargs={
                    'show_as_editable': True,
                    'allow_reordering': False,  # Disable reordering for system-defined attributes
                }
            )
            subsystem_formset_list.append(subsystem_formset)
        
        return subsystem_formset_list

    def validate_all_formsets(
            self,
            subsystem_formset_list: List[SubsystemAttributeFormSet]
    ) -> bool:
        """Validate all subsystem formsets."""
        all_valid = True
        for formset in subsystem_formset_list:
            if not formset.is_valid():
                all_valid = False
        return all_valid

    def save_all_formsets(
            self,
            subsystem_formset_list: List[SubsystemAttributeFormSet],
            request: HttpRequest
    ) -> None:
        """Save all formsets within a transaction."""
        with transaction.atomic():
            for formset in subsystem_formset_list:
                formset.save()

    def create_initial_context(self, selected_subsystem_id: str = None) -> Dict[str, Any]:
        """Create initial template context for config settings editing."""
        subsystem_formset_list = self.create_config_forms()
        
        # Determine selected subsystem ID (default to first if none provided)
        if selected_subsystem_id is None and subsystem_formset_list:
            selected_subsystem_id = str(subsystem_formset_list[0].instance.id)
        
        # Create paired data objects with formsets and their contexts
        subsystem_edit_data_list = [
            SubsystemAttributeEditData(
                formset=formset,
                context=SubsystemAttributeEditContext(formset.instance),
                error_count=0  # No errors on initial load
            )
            for formset in subsystem_formset_list
        ]
        
        # Special case: Subsystem editing combines multiple Subsystem objects 
        # into a single editing context (unlike Entity/Location's one-to-one relationship).
        # Provide the shared context for container IDs and namespacing.
        shared_context = subsystem_edit_data_list[0].context if subsystem_edit_data_list else None
        
        return {
            'subsystem_edit_data_list': subsystem_edit_data_list,
            'selected_subsystem_id': selected_subsystem_id,
            'shared_editing_context': shared_context,  # For container IDs and namespacing
        }

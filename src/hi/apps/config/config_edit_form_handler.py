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

    def create_initial_context(self) -> Dict[str, Any]:
        """Create initial template context for config settings editing."""
        subsystem_formset_list = self.create_config_forms()
        
        return {
            'subsystem_attribute_formset_list': subsystem_formset_list,
            'history_url_name': 'config_attribute_history',
            'restore_url_name': 'config_attribute_restore',
        }

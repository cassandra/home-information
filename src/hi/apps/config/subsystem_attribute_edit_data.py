"""
SubsystemAttributeEditData - Data container for pairing formsets with their contexts.
"""
from dataclasses import dataclass

from .forms import SubsystemAttributeFormSet
from .subsystem_attribute_edit_context import SubsystemAttributeEditContext
from .models import Subsystem


@dataclass
class SubsystemAttributeEditData:
    """Container that pairs a subsystem formset with its attribute edit context."""
    
    formset: SubsystemAttributeFormSet
    context: SubsystemAttributeEditContext
    error_count: int = 0
    
    @property
    def subsystem(self) -> Subsystem:
        """Get the Subsystem instance."""
        return self.formset.instance

"""
SubsystemAttributeEditContext - Subsystem-specific context for attribute editing templates.
"""
from hi.apps.attribute.edit_context import AttributeEditContext
from .models import Subsystem


class SubsystemAttributeEditContext(AttributeEditContext):
    """Subsystem-specific context provider for attribute editing templates."""
    
    def __init__(self, subsystem: Subsystem) -> None:
        """Initialize context for Subsystem attribute editing."""
        # Use 'subsystem' as owner_type to match URL patterns
        super().__init__(subsystem, 'subsystem')
    
    @property
    def subsystem(self) -> Subsystem:
        """Get the Subsystem instance (typed accessor)."""
        return self.owner

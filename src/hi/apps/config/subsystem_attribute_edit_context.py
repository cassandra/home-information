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
    
    @property
    def id_suffix(self) -> str:
        """
        Override to provide simple subsystem suffix (no ID needed).
        
        Since there's only one subsystem configuration context,
        we don't need the numeric ID like entity/location contexts.
        
        Returns:
            str: Simple suffix '-subsystem'
        """
        return '-subsystem'

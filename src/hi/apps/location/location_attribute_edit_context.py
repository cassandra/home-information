"""
LocationAttributeEditContext - Location-specific context for attribute editing templates.

This module contains Location-specific implementations of the AttributeEditContext
pattern, encapsulating location-specific domain knowledge while maintaining
the generic template interface.
"""
from typing import Any

from hi.apps.attribute.edit_context import AttributeEditContext
from .models import Location


class LocationAttributeEditContext(AttributeEditContext):
    """
    Location-specific context provider for attribute editing templates.
    
    This class encapsulates Location-specific knowledge while providing
    the generic interface expected by attribute editing templates.
    """
    
    def __init__(self, location: Location) -> None:
        """
        Initialize context for Location attribute editing.
        
        Args:
            location: The Location instance that owns the attributes
        """
        super().__init__(location, 'location')
    
    @property
    def location(self) -> Location:
        """Get the Location instance (typed accessor)."""
        return self.owner
"""
EntityAttributeEditContext - Entity-specific context for attribute editing templates.

This module contains Entity-specific implementations of the AttributeEditContext
pattern, encapsulating entity-specific domain knowledge while maintaining
the generic template interface.
"""
from typing import Any

from hi.apps.attribute.edit_context import AttributeEditContext
from .models import Entity


class EntityAttributeEditContext(AttributeEditContext):
    """
    Entity-specific context provider for attribute editing templates.
    
    This class encapsulates Entity-specific knowledge while providing
    the generic interface expected by attribute editing templates.
    """
    
    def __init__(self, entity: Entity) -> None:
        """
        Initialize context for Entity attribute editing.
        
        Args:
            entity: The Entity instance that owns the attributes
        """
        super().__init__(entity, 'entity')
    
    @property
    def entity(self) -> Entity:
        """Get the Entity instance (typed accessor)."""
        return self.owner
"""
AttributeEditContext - Generic context provider for attribute editing templates.

This class provides a clean abstraction that allows attribute editing templates
to work generically across different owner types (Entity, Location, etc.) while
maintaining type safety and clear URL routing patterns.
"""
from typing import Any, Dict


class AttributeEditContext:
    """
    Context provider for attribute editing templates that abstracts away
    owner-specific details (entity vs location vs future types).
    
    This allows templates to be completely generic while providing
    type-safe access to owner information, URLs, and DOM identifiers.
    """
    
    def __init__(self, owner: Any, owner_type: str) -> None:
        """
        Initialize context for attribute editing.
        
        Args:
            owner: The model instance that owns the attributes (Entity, Location, etc.)
            owner_type: String identifier for the owner type ("entity", "location", etc.)
        """
        self.owner = owner
        self.owner_type = owner_type.lower()
    
    @property
    def owner_id(self) -> int:
        """Get the owner's primary key ID."""
        return self.owner.id
    
    @property
    def owner_id_param_name(self) -> str:
        """Get the URL parameter name for owner ID (e.g., 'entity_id', 'location_id')."""
        return f'{self.owner_type}_id'
    
    @property
    def owner_name(self) -> str:
        """Get the owner's display name."""
        return self.owner.name
    
    @property
    def history_url_name(self) -> str:
        """Get the URL name for inline attribute history view."""
        return f'{self.owner_type}_attribute_history_inline'
    
    @property
    def restore_url_name(self) -> str:
        """Get the URL name for inline attribute restore view."""
        return f'{self.owner_type}_attribute_restore_inline'
    
    def history_target_id(self, attribute_id: int) -> str:
        """
        Get the DOM ID for the attribute history container.
        
        Args:
            attribute_id: The attribute's primary key
            
        Returns:
            str: DOM ID for the history container
        """
        return f'hi-{self.owner_type}-attr-history-{self.owner_id}-{attribute_id}'
    
    def history_toggle_id(self, attribute_id: int) -> str:
        """
        Get the DOM ID for the history toggle/collapse target.
        
        Args:
            attribute_id: The attribute's primary key
            
        Returns:
            str: DOM ID for the history toggle target
        """
        return f'history-extra-{self.owner_id}-{attribute_id}'
    
    def file_title_field_name(self, attribute_id: int) -> str:
        """
        Get the form field name for file title editing.
        
        Args:
            attribute_id: The attribute's primary key
            
        Returns:
            str: Form field name for file title
        """
        return f'file_title_{self.owner_id}_{attribute_id}'
    
    # Container-based ID generation for multi-instance support
    @property
    def id_suffix(self) -> str:
        """
        Get the suffix to append to DIVID constants for unique element IDs.
        
        This creates namespaced IDs that prevent conflicts when multiple 
        attribute editing contexts exist on the same page.
        
        Returns:
            str: Suffix like '-entity-123' or '-location-456'
        """
        return f'-{self.owner_type}-{self.owner_id}'
    
    @property
    def container_html_id(self) -> str:
        """Get unique ID for the root container element."""
        return f'attr-v2-container{self.id_suffix}'
    
    @property
    def content_html_id(self) -> str:
        """Get unique ID for the main content area (antinode target)."""
        return f'attr-v2-content{self.id_suffix}'
    
    @property
    def status_msg_html_id(self) -> str:
        """Get unique ID for the status message area (antinode target)."""
        return f'attr-v2-status-msg{self.id_suffix}'
    
    @property
    def dirty_msg_html_id(self) -> str:
        """Get unique ID for the dirty message area."""
        return f'attr-v2-dirty-message{self.id_suffix}'
    
    @property
    def form_html_id(self) -> str:
        """Get unique ID for the main form element."""
        return f'attr-v2-form{self.id_suffix}'
    
    @property
    def file_input_html_id(self) -> str:
        """Get unique ID for the file input element."""
        return f'attr-v2-file-input{self.id_suffix}'
    
    @property
    def upload_form_container_html_id(self) -> str:
        """Get unique ID for the upload form container element."""
        return f'attr-v2-upload-form-container{self.id_suffix}'
    
    def to_template_context(self) -> Dict[str, Any]:
        """
        Convert this context to a dictionary suitable for template rendering.
        
        Returns:
            dict: Template context variables
        """
        return {
            'attr_context': self,
            # Provide the owner under both generic and specific names for compatibility
            'owner': self.owner,
            self.owner_type: self.owner,  # e.g., 'entity': self.owner or 'location': self.owner
        }
    

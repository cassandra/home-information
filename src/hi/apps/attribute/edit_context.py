"""
AttributeEditContext - Generic context provider for attribute editing templates.

This class provides a clean abstraction that allows attribute editing templates
to work generically across different owner types (Entity, Location, etc.) while
maintaining type safety and clear URL routing patterns.
"""
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet

from hi.constants import DIVID

from .models import AttributeModel


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
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        raise NotImplementedError('Subclasses must override this method')
            
    @property
    def formset_prefix(self) -> str:
        return f'{self.owner_type}-{self.owner.id}'

    def create_owner_form( self, form_data : Optional[ Dict[str, Any] ] = None ) -> ModelForm:
        """ Subclasses can override this if there are model properties of the owner model itself
        that should be included in the attribute editing interface."""
        return None

    def create_regular_attributes_formset(
            self, form_data : Optional[ Dict[str, Any] ] = None ) -> BaseInlineFormSet:
        """ Formset should extend BaseInlineFormSet.  (should exclude FILE attributes) """
        raise NotImplementedError('Subclasses must override this method')

    def attributes_queryset(self):
        """ Default is that AttributeModel suibclass has 'attributes' as the related name for 
        the owner model. """
        return self.owner.attributes

    @property
    def content_body_template_name(self):
        """ This should be a template that extends attribute/components/edit_content_body.html """
        raise NotImplementedError('Subclasses must override this method')
    
    @property
    def file_upload_url(self) -> str:
        """ Should be a view that extends BaseAttributeUploadView """
        raise NotImplementedError('Subclasses must override this method')
    
    @property
    def history_url_name(self) -> str:
        """ Should be a view that extends BaseAttributeHistoryView """
        return f'{self.owner_type}_attribute_history_inline'
    
    @property
    def restore_url_name(self) -> str:
        """ Should be a view that extends BaseAttributeRestoreView """
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
        return f"{DIVID['ATTR_V2_CONTAINER_ID']}{self.id_suffix}"
    
    @property
    def content_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_CONTENT_ID']}{self.id_suffix}"
    
    @property
    def update_button_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_UPDATE_BTN_ID']}{self.id_suffix}"
    
    @property
    def status_msg_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_STATUS_MESSAGE_ID']}{self.id_suffix}"
    
    @property
    def dirty_msg_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_DIRTY_MESSAGE_ID']}{self.id_suffix}"
    
    @property
    def form_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_FORM_ID']}{self.id_suffix}"
    
    @property
    def file_input_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_FILE_INPUT_ID']}{self.id_suffix}"
    
    @property
    def file_grid_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_FILE_GRID_ID']}{self.id_suffix}"
    
    @property
    def upload_form_container_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER_ID']}{self.id_suffix}"
    
    @property
    def scrollable_content_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_SCROLLABLE_CONTENT_ID']}{self.id_suffix}"

    @property
    def add_attribute_button_html_id(self) -> str:
        return f"{DIVID['ATTR_V2_ADD_ATTRIBUTE_BTN_ID']}{self.id_suffix}"
    
    def to_template_context(self) -> Dict[str, Any]:
        """
        Convert this context to a dictionary suitable for template rendering.
        
        Returns:
            dict: Template context variables
        """
        return {
            "owner": self.owner,
            "attr_context": self,

            # Duplicate with explicit naming for convenience.
            self.owner_type: self.owner,  # e.g., "entity": self.owner or "location": self.owner
        }
    

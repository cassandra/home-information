"""
EntityAttributeItemEditContext - Entity-specific context for attribute editing templates.

This module contains Entity-specific implementations of the AttributeItemEditContext
pattern, encapsulating entity-specific domain knowledge while maintaining
the generic template interface.
"""
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet
from django.urls import reverse

from hi.apps.attribute.edit_context import AttributeItemEditContext
from hi.apps.attribute.models import AttributeModel

from .forms import EntityForm, EntityAttributeRegularFormSet
from .models import Entity, EntityAttribute


class EntityAttributeItemEditContext(AttributeItemEditContext):
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
        super().__init__( owner_type = 'entity', owner = entity )
        return
    
    @property
    def entity(self) -> Entity:
        """Get the Entity instance (typed accessor)."""
        return self.owner
    
    @property
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        return EntityAttribute
    
    def create_owner_form( self, form_data : Optional[ Dict[str, Any] ] = None ) -> ModelForm:
        return EntityForm( form_data, instance = self.entity )
    
    def create_regular_attributes_formset(
            self, form_data : Optional[ Dict[str, Any] ] = None ) -> BaseInlineFormSet:
        return EntityAttributeRegularFormSet(
            form_data,
            instance = self.entity,
            prefix = self.formset_prefix,
        )

    @property
    def content_body_template_name(self):
        return 'entity/panes/entity_edit_content_body.html'
    
    @property
    def file_upload_url(self) -> str:
        return reverse( 'entity_attribute_upload',
                        kwargs = { 'entity_id': self.entity.id })

"""
Subsystem Attribute Edit Context - Subsystem-specific context for attribute editing templates.
"""
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet

from hi.apps.attribute.edit_context import AttributeItemEditContext, AttributePageEditContext
from hi.apps.attribute.forms import AttributeUploadForm
from hi.apps.attribute.models import AttributeModel

from .forms import SubsystemAttributeFormSet

from .models import Subsystem, SubsystemAttribute


class SubsystemAttributePageEditContext(AttributePageEditContext):

    def __init__( self, selected_subsystem_id : str ) -> None:
        """Initialize context for Subsystem attribute editing."""
        # Use 'subsystem' as owner_type to match URL patterns
        super().__init__( owner_type = 'subsystem' )
        self.selected_subsystem_id = selected_subsystem_id
        return
    
    @property
    def content_body_template_name(self):
        return 'config/panes/subsystem_edit_content_body.html'

    def to_template_context(self) -> Dict[str, Any]:
        template_context = super().to_template_context()
        template_context.update({
            "selected_subsystem_id": self.selected_subsystem_id,
        })
        return template_context
    

class SubsystemAttributeItemEditContext(AttributeItemEditContext):
    
    def __init__( self, subsystem: Subsystem ) -> None:
        """Initialize context for Subsystem attribute editing."""
        # Use 'subsystem' as owner_type to match URL patterns
        super().__init__( owner_type = 'subsystem', owner = subsystem )
        return
    
    @property
    def subsystem(self) -> Subsystem:
        """Get the Subsystem instance (typed accessor)."""
        return self.owner
    
    @property
    def content_body_template_name(self):
        return 'config/panes/subsystem_edit_content_body.html'

    @property
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        return SubsystemAttribute
    
    def create_owner_form( self, form_data : Optional[ Dict[str, Any] ] = None ) -> ModelForm:
        # No viewable/editable Subsystem properties.
        return None

    def create_attribute_model( self ) -> AttributeModel:
        return SubsystemAttribute( subsystem = self.subsystem )
        
    def create_regular_attributes_formset(
            self, form_data : Optional[ Dict[str, Any] ] = None ) -> BaseInlineFormSet:
        return SubsystemAttributeFormSet(
            form_data,
            instance = self.subsystem,
            prefix = self.formset_prefix,
            form_kwargs={
                'show_as_editable': True,
                'allow_reordering': False,  # Disable reordering for system-defined attributes
            }
        )

    @property
    def attribute_upload_form_class(self) -> Type[AttributeUploadForm]:
        # No file uploads for Subsystem attributes (as of yet)
        return None
    
    @property
    def file_upload_url(self) -> str:
        # No file uploads for Subsystem attributes (as of yet)
        return None

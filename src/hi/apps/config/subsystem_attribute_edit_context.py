"""
Subsystem Attribute Edit Context - Subsystem-specific context for attribute editing templates.
"""
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet
from django.urls import reverse

from hi.apps.attribute.edit_context import AttributeItemEditContext, AttributePageEditContext
from hi.apps.attribute.forms import AttributeUploadForm
from hi.apps.attribute.models import AttributeModel

from .forms import SubsystemAttributeFormSet, SubsystemAttributeUploadForm

from .models import Subsystem, SubsystemAttribute


class SubsystemAttributePageEditContext(AttributePageEditContext):

    def __init__( self ) -> None:
        """Initialize context for Subsystem attribute editing."""
        # Use 'subsystem' as owner_type to match URL patterns
        super().__init__( owner_type = 'subsystem' )
        return
    
    @property
    def content_body_template_name(self):
        return 'config/panes/config_settings_content_body.html'


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
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        return SubsystemAttribute
    
    @property
    def attribute_upload_form_class(self) -> Type[AttributeUploadForm]:
        return SubsystemAttributeUploadForm
    
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
    def file_upload_url(self) -> str:
        return reverse( 'subsystem_attribute_upload',
                        kwargs = { 'subsystem_id': self.subsystem.id })
            

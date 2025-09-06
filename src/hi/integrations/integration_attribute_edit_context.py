"""
Integration Attribute Edit Context - Integration-specific context for attribute editing templates.

This module contains Integration-specific implementations of the AttributeItemEditContext
pattern, encapsulating integration-specific domain knowledge while maintaining
the generic template interface.
"""
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet

from hi.apps.attribute.edit_context import AttributeItemEditContext
from hi.apps.attribute.forms import AttributeUploadForm
from hi.apps.attribute.models import AttributeModel

from .forms import IntegrationAttributeRegularFormSet
from .integration_data import IntegrationData
from .models import Integration, IntegrationAttribute


class IntegrationAttributeItemEditContext(AttributeItemEditContext):
    """
    Integration-specific context provider for attribute editing templates.
    
    This class encapsulates Integration-specific knowledge while providing
    the generic interface expected by attribute editing templates.
    """
    
    def __init__(self,
                 integration_data: IntegrationData,
                 update_button_label = 'UPDATE',
                 suppress_history = False,
                 show_secrets = False,
                 ) -> None:
        """
        Initialize context for Integration attribute editing.
        
        Args:
            integration: The Integration instance that owns the attributes
        """
        super().__init__( owner_type = 'integration', owner = integration_data.integration )
        self.integration_data = integration_data
        self._update_button_label = update_button_label
        self._suppress_history = suppress_history
        self._show_secrets = show_secrets
        
        return
    
    @property
    def integration(self) -> Integration:
        """Get the Integration instance (typed accessor)."""
        return self.owner
    
    @property
    def content_body_template_name(self):
        return 'integrations/panes/integration_edit_content_body.html'
    
    @property
    def update_button_label(self) -> str:
        return self._update_button_label
    
    @property
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        return IntegrationAttribute

    def create_owner_form( self, form_data : Optional[ Dict[str, Any] ] = None ) -> ModelForm:
        # No viewable/editable Integration model properties.
        return None

    def create_attribute_model( self ) -> AttributeModel:
        return IntegrationAttribute( integration = self.integration )
    
    def create_regular_attributes_formset(
            self, form_data : Optional[ Dict[str, Any] ] = None ) -> BaseInlineFormSet:
        return IntegrationAttributeRegularFormSet(
            form_data,
            instance = self.integration,
            prefix = self.formset_prefix,
            form_kwargs={
                'show_as_editable': True,
                'allow_reordering': False,  # Disable reordering for system-defined attributes
                'suppress_history': self._suppress_history,  # While enabling, no history
                'show_secrets': self._show_secrets,  # While enable, plain password view
            }
        )

    @property
    def attribute_upload_form_class(self) -> Type[AttributeUploadForm]:
        # No file uploads for Integration attributes (as of yet)
        return None
    
    @property
    def file_upload_url(self) -> str:
        # No file uploads for Integration attributes (as of yet)
        return None
    
    def to_template_context(self) -> Dict[str, Any]:
        template_context = super().to_template_context()
        template_context.update({
            'integration_data': self.integration_data,
        })
        return template_context

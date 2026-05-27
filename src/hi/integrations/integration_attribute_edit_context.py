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
from hi.apps.system.health_status import HealthStatus

from hi.integrations.capability_gateway import CapabilityGateway
from hi.integrations.forms import IntegrationAttributeRegularFormSet
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from .integration_data import IntegrationData


class IntegrationAttributeItemEditContext(AttributeItemEditContext):
    """
    Integration-specific context provider for attribute editing templates.

    This class encapsulates Integration-specific knowledge while providing
    the generic interface expected by attribute editing templates.

    Construction takes the active ``CapabilityGateway`` directly (rather
    than the capability enum). The instance carries both the capability
    identity (``capability_gateway.capability``) used for attribute
    filtering and the capability-specific UI hooks (description,
    attribute-form action template) the rendered templates consult.
    """

    def __init__( self,
                  integration_data     : IntegrationData,
                  capability_gateway   : Optional[ CapabilityGateway ],
                  health_status        : HealthStatus      = None,
                  update_button_label  : str               = 'UPDATE',
                  suppress_history     : bool              = False,
                  show_secrets         : bool              = False,
                  ) -> None:
        super().__init__( owner_type = 'integration', owner = integration_data.integration )
        self.integration_data = integration_data
        self._capability_gateway = capability_gateway
        # capability_gateway may be None in legacy paths (e.g., an
        # integration declares a capability metadata-side but
        # exposes no implementation instance). The attribute
        # queryset falls back to "no capability filter" in that
        # case, which preserves existing behavior.
        self._capability = (
            capability_gateway.capability if capability_gateway is not None else None
        )
        self._health_status = health_status
        self._update_button_label = update_button_label
        self._suppress_history = suppress_history
        self._show_secrets = show_secrets

        return
    
    @property
    def integration(self) -> Integration:
        """Get the Integration instance (typed accessor)."""
        return self.owner
    
    @property
    def can_restore_default(self):
        return False
    
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
            queryset = self._capability_filtered_attribute_queryset(),
            prefix = self.formset_prefix,
            form_kwargs={
                'show_as_editable': True,
                'allow_reordering': False,
                'suppress_history': self._suppress_history,
                'show_secrets': self._show_secrets,
            }
        )

    def _capability_filtered_attribute_queryset(self):
        AttributeType = self.integration_data.integration_metadata.attribute_type
        key_strs = [
            IntegrationKey(
                integration_id = self.integration.integration_id,
                integration_name = str( member ),
            ).integration_key_str
            for member in AttributeType
            if self._capability is None or self._capability in member.capabilities
        ]
        return self.integration.attributes.filter(
            integration_key_str__in = key_strs,
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
            'health_status': self._health_status,
            'capability_gateway': self._capability_gateway,
        })
        return template_context

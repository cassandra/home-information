"""
Framework-level integration views shared across capabilities.
"""
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.hi_async_view import HiModalView

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_attribute_edit_context import (
    IntegrationAttributeItemEditContext,
)
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.view_mixins import (
    CapabilityBlockViewMixin,
    IntegrationViewMixin,
)


class CapabilityConfigureView( HiModalView,
                               IntegrationViewMixin,
                               CapabilityBlockViewMixin,
                               AttributeEditViewMixin ):
    """Base for the per-capability credentials Configure modal.

    Subclasses set the four class-level constants and override
    ``handle_post_success`` to define what happens after credentials
    save. The base owns:
      * the GET render flow (block check → ensure_all_attributes_exist →
        build edit context → render modal)
      * the POST save flow (post_attribute_form → delegate to subclass)
      * the ``validate_attributes_extra`` hook for AttributeEditViewMixin.

    Subclasses own the timing of ``notify_settings_changed()`` because
    the right moment is capability-specific: Connect-side managers
    gate client (re)build on ``integration.is_enabled``, so the notify
    must fire AFTER ``enable_integration``; Import flows fire it
    before reading candidates.
    """

    capability    : IntegrationCapability  = None
    button_label  : str                    = None
    template_name : str                    = None
    error_title   : str                    = None

    def get_template_name( self ) -> str:
        return self.template_name

    def _build_attr_item_context( self, integration_data ):
        return IntegrationAttributeItemEditContext(
            integration_data       = integration_data,
            capability             = self.capability,
            update_button_label    = self.button_label,
            suppress_history       = True,
            show_secrets           = True,
        )

    def get(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_data = self.get_integration_data( request, *args, **kwargs )

        block_response = self.render_capability_block_if_conflict(
            request = request,
            integration_data = integration_data,
            capability_being_initiated = self.capability,
        )
        if block_response is not None:
            return block_response

        integration_manager.ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )
        attr_item_context = self._build_attr_item_context( integration_data )
        template_context = self.create_initial_template_context(
            attr_item_context = attr_item_context,
        )
        return self.modal_response( request, template_context )

    def post(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )

        # Re-check the mode-switch invariant on POST. The GET path
        # already runs this, but a direct POST (cached form, replayed
        # request) would otherwise bypass it.
        block_response = self.render_capability_block_if_conflict(
            request = request,
            integration_data = integration_data,
            capability_being_initiated = self.capability,
        )
        if block_response is not None:
            return block_response

        attr_item_context = self._build_attr_item_context( integration_data )
        response = self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )
        # Errors re-render the form with messages.
        if response.status_code > 299:
            return response
        return self.handle_post_success( request, integration_data )

    def handle_post_success( self, request, integration_data ):
        raise NotImplementedError( 'Subclasses must override.' )

    def validate_attributes_extra( self,
                                   attr_item_context,
                                   regular_attributes_formset,
                                   request ):
        """ Override for AttributeEditViewMixin """
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = self.error_title,
        )
        return

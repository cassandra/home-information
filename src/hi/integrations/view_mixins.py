from django.http import Http404

from .integration_manager import IntegrationManager


class IntegrationViewMixin:

    def get_integration_data( self, integration_id : str ):
        try:
            return IntegrationManager().get_integration_data(
                integration_id = integration_id,
            )
        except KeyError:
            raise Http404()
        return
    
    def get_integration_data_list( self, enabled_only = False ):
        return IntegrationManager().get_integration_data_list(
            enabled_only = enabled_only,
        )
    
    def validate_attributes_extra_helper( self,
                                          attr_item_context,
                                          regular_attributes_formset,
                                          error_title ):
        """
        Validate the proposed integration configuration in two stages:
          1. Schema-level check via gateway.validate_configuration (offline,
             fast). Catches structural problems with the attribute set.
          2. Live connection probe via gateway.test_connection bounded by
             IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS. Catches
             unreachable upstream / bad credentials so the user sees the
             specific reason inline rather than experiencing a silent
             save followed by a delayed background error.

        Both gateway methods are required by their contracts to never
        throw — they convert any internal exception into the appropriate
        result type (IntegrationValidationResult.error /
        ConnectionTestResult.failure) carrying a human-readable message.
        We deliberately do NOT wrap their invocations in a broad try/
        except here: doing so would coerce the gateway's specific
        failure message into a generic catch-all string, and would also
        hide genuine programming bugs (which should surface through
        Django's error pipeline rather than be silently translated into
        a form-level error).
        """
        integration_data = attr_item_context.integration_data
        gateway = integration_data.integration_gateway

        # Get current attribute values from the formset
        integration_attributes = []
        for form in regular_attributes_formset:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # Create a temporary attribute-like object with the form data
                attr_instance = form.instance
                attr_instance.value = form.cleaned_data.get('value', '')
                integration_attributes.append(attr_instance)

        # Stage 1: schema-only validation.
        validation_result = gateway.validate_configuration(
            integration_attributes
        )
        if not validation_result.is_valid:
            error_message = validation_result.error_message or 'Configuration is invalid'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )
            return

        # Stage 2: live connection probe with bounded timeout.
        test_result = gateway.test_connection(
            integration_attributes = integration_attributes,
            timeout_secs = IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS,
        )
        if not test_result.is_success:
            error_message = test_result.message or 'Connection test failed'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )
        return


    

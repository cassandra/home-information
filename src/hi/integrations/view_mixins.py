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
        """Validate API connectivity before enabling integration."""
        # Get the integration data from the context
        integration_data = attr_item_context.integration_data
        
        try:
            # Get current attribute values from the formset
            integration_attributes = []
            for form in regular_attributes_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    # Create a temporary attribute-like object with the form data
                    attr_instance = form.instance
                    attr_instance.value = form.cleaned_data.get('value', '')
                    integration_attributes.append(attr_instance)
            
            validation_result = integration_data.integration_gateway.validate_configuration(
                integration_attributes
            )

            if not validation_result.is_valid:
                error_message = validation_result.error_message or 'API validation failed'
                regular_attributes_formset._non_form_errors.append(
                    f'{error_title}: {error_message}'
                )
                
        except Exception as e:
            error_message = f'API validation error: {e}'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )


    

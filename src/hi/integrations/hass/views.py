import json

from django.core.exceptions import BadRequest
from django.db import transaction

from django.shortcuts import render
from django.views.generic import View

from hi.integrations.core.forms import IntegrationAttributeFormSet
from hi.integrations.core.helpers import IntegrationHelperMixin

from hi.hi_async_view import HiModalView

from .hass_metadata import HassMetaData
from .hass_mixins import HassMixin
from .hass_sync import HassSynchronizer


class HassSettingsView( View, IntegrationHelperMixin, HassMixin ):

    def post( self, request, *args, **kwargs ):

        integration = self.get_or_create_integration(
            integration_metadata = HassMetaData,
        )
        if not integration.is_enabled:
            raise BadRequest( 'HAss is not enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration,
            prefix = f'integration-{integration.id}',
        )
        if integration_attribute_formset.is_valid():
            with transaction.atomic():
                integration_attribute_formset.save()

            self.hass_manager().notify_settings_changed()

        context = {
            'integration_attribute_formset': integration_attribute_formset,
        }
        return render( request, 'hass/panes/hass_settings.html', context )

    
class HassSyncView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'common/modals/processing_result.html'

    def post(self, request, *args, **kwargs):

        processing_result = HassSynchronizer().sync()
        context = {
            'processing_result': processing_result,
        }
        return self.modal_response( request, context )

    
class SyensorResponseDetailsView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'hass/modals/sensor_response_details.html'

    def get(self, request, *args, **kwargs):
        details_str = kwargs.get( 'details_str' )

        # TODO: No current HAss SensorResponse instances add any viewable details.
        details_dict = json.loads( details_str )
        context = details_dict
        return self.modal_response( request, context )

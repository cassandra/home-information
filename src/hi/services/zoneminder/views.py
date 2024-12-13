from django.core.exceptions import BadRequest
from django.db import transaction
from django.shortcuts import render
from django.views.generic import View

from hi.integrations.forms import IntegrationAttributeFormSet
from hi.integrations.integration_manager import IntegrationManager

from hi.hi_async_view import HiModalView

from .zm_mixins import ZoneMinderMixin
from .zm_metadata import ZmMetaData
from .zm_sync import ZoneMinderSynchronizer


class ZmSettingsView( View, ZoneMinderMixin ):

    def post( self, request, *args, **kwargs ):
        integration_data = IntegrationManager().get_integration_data(
            integration_id = ZmMetaData.integration_id,
        )
        if not integration_data.is_enabled:
            raise BadRequest( 'ZoneMinder is not enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration_data.integration,
            prefix = f'integration-{integration_data.integration_id}',
        )
        if integration_attribute_formset.is_valid():
            with transaction.atomic():
                integration_attribute_formset.save()

            self.zm_manager().notify_settings_changed()
                
        context = {
            'integration_attribute_formset': integration_attribute_formset,
        }
        return render( request, 'zoneminder/panes/zm_settings.html', context )
    
    
class ZmSyncView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'common/modals/processing_result.html'

    def post(self, request, *args, **kwargs):

        processing_result = ZoneMinderSynchronizer().sync()
        context = {
            'processing_result': processing_result,
        }
        return self.modal_response( request, context )

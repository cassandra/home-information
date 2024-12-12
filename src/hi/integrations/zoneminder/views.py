from django.core.exceptions import BadRequest
from django.db import transaction
from django.shortcuts import render
from django.views.generic import View

from hi.integrations.core.forms import IntegrationAttributeFormSet
from hi.integrations.core.helpers import IntegrationHelperMixin

from hi.hi_async_view import HiModalView

from .zm_mixins import ZoneMinderMixin
from .zm_metadata import ZmMetaData
from .zm_sync import ZoneMinderSynchronizer


class ZmSettingsView( View, IntegrationHelperMixin, ZoneMinderMixin ):

    def post( self, request, *args, **kwargs ):

        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if not integration.is_enabled:
            raise BadRequest( 'ZoneMinder not is enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration,
            prefix = f'integration-{integration.id}',
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

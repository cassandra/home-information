from django.core.exceptions import BadRequest
from django.db import transaction
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.integrations.core.forms import IntegrationAttributeFormSet
from hi.integrations.core.helpers import IntegrationHelperMixin
from hi.integrations.core.views import IntegrationPageView

from hi.constants import DIVID
from hi.hi_async_view import HiAsyncView, HiModalView

from .zm_manager import ZoneMinderManager
from .zm_metadata import ZmMetaData


class ZmEnableView( HiModalView, IntegrationHelperMixin ):

    def get_template_name( self ) -> str:
        return 'zoneminder/modals/zm_enable.html'

    def get(self, request, *args, **kwargs):
        
        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if integration.is_enabled:
            raise BadRequest( 'ZoneMinder is already enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration,
            prefix = f'integration-{integration.id}',
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        context = {
            'integration_attribute_formset': integration_attribute_formset,
        }
        return self.modal_response( request, context )

    def post(self, request, *args, **kwargs):

        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if integration.is_enabled:
            raise BadRequest( 'ZoneMinder is already enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration,
            prefix = f'integration-{integration.id}',
        )
        if not integration_attribute_formset.is_valid():
            context = {
                'integration_attribute_formset': integration_attribute_formset,
            }
            return self.modal_response( request, context, status_code = 400 )

        with transaction.atomic():
            integration.is_enabled = True
            integration.save()
            integration_attribute_formset.save()

        redirect_url = reverse( 'zm_manage' )
        return self.redirect_response( request, redirect_url )
    
    
class ZmDisableView( HiModalView, IntegrationHelperMixin ):

    def get_template_name( self ) -> str:
        return 'zoneminder/modals/zm_disable.html'

    def get(self, request, *args, **kwargs):
        context = {
        }
        return self.modal_response( request, context )
    
    
class ZmManageView( IntegrationPageView, IntegrationHelperMixin ):

    @property
    def integration_metadata(self):
        return ZmMetaData
    
    def get_main_template_name( self ) -> str:
        return 'zoneminder/panes/zm_manage.html'

    def get_template_context( self, request, *args, **kwargs ):

        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if not integration.is_enabled:
            raise BadRequest( 'ZoneMinder is not enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration,
            prefix = f'integration-{integration.id}',
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        return {
            'integration_metadata': ZmMetaData,
            'integration_attribute_formset': integration_attribute_formset,
        }


class ZmSettingsView( HiAsyncView, IntegrationHelperMixin ):

    def get_target_div_id( self ) -> str:
        return DIVID['INTEGRATION_SETTINGS_PANE']

    def get_template_name( self ) -> str:
        return 'zoneminder/panes/zm_settings.html'

    def post_template_context( self, request, *args, **kwargs ):

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

        context = {
            'integration_attribute_formset': integration_attribute_formset,
        }
        return context
    
    
class ZmSyncView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'common/modals/processing_result.html'

    def post(self, request, *args, **kwargs):

        processing_result = ZoneMinderManager().sync()
        context = {
            'processing_result': processing_result,
        }
        return self.modal_response( request, context )
    

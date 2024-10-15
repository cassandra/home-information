from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.integrations.core.forms import IntegrationAttributeFormSet
from hi.integrations.core.helpers import IntegrationHelperMixin

from .hass_metadata import HassMetaData
from .hass_manager import HassManager


class HassEnableView( View, IntegrationHelperMixin ):

    def get(self, request, *args, **kwargs):
        
        integration = self.get_or_create_integration(
            integration_metadata = HassMetaData,
        )
        if integration.is_enabled:
            raise BadRequest( 'HAss is already enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration,
            form_kwargs = {
                'is_editable': True,
            },
        )
        return self.get_modal_response(
            request = request,
            integration_attribute_formset = integration_attribute_formset,
        )

    def post(self, request, *args, **kwargs):

        integration = self.get_or_create_integration(
            integration_metadata = HassMetaData,
        )
        if integration.is_enabled:
            raise BadRequest( 'HAss is already enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            instance = integration,
        )
        if not integration_attribute_formset.is_valid():
            return self.get_modal_response(
                request = request,
                integration_attribute_formset = integration_attribute_formset,
                status = 400,
            )

        with transaction.atomic():
            integration.is_enabled = True
            integration.save()
            integration_attribute_formset.save()

        return antinode.refresh_response()

    def get_modal_response( self,
                            request                        : HttpRequest,
                            integration_attribute_formset  : IntegrationAttributeFormSet,
                            status                         : int                        = 200 ):
        context = {
            'integration_attribute_formset': integration_attribute_formset,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'hass/modals/hass_enable.html',
            context = context,
            status = status,
        )

    
class HassDisableView( View ):

    def get(self, request, *args, **kwargs):

        context = {
        }
        return render( request, 'hass/modals/hass_disable.html', context )
    
    
class HassManageView( View ):

    def get(self, request, *args, **kwargs):

        context = {
            'integration_metadata': HassMetaData,
        }
        return render( request, 'hass/panes/manage.html', context )
    
    
class HassSyncView( View ):

    def post(self, request, *args, **kwargs):

        processing_result = HassManager().sync()
        
        context = {
            'integration_metadata': HassMetaData,
            'processing_result': processing_result,
        }
        return render( request, 'hass/panes/manage.html', context )
    

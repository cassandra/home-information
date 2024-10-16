from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import render
from django.template.loader import get_template
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.integrations.core.forms import IntegrationAttributeFormSet
from hi.integrations.core.helpers import IntegrationHelperMixin

from hi.constants import DIVID

from .zm_manager import ZoneMinderManager
from .zm_metadata import ZmMetaData


class ZmEnableView( View, IntegrationHelperMixin ):

    def get(self, request, *args, **kwargs):
        
        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if integration.is_enabled:
            raise BadRequest( 'ZoneMinder is already enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration,
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        return self.get_modal_response(
            request = request,
            integration_attribute_formset = integration_attribute_formset,
        )

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
            template_name = 'zoneminder/modals/zm_enable.html',
            context = context,
            status = status,
        )
    
    
class ZmDisableView( View ):

    def get(self, request, *args, **kwargs):

        context = {
        }
        return render( request, 'zoneminder/modals/zm_disable.html', context )
    
    
class ZmManageView( View, IntegrationHelperMixin ):

    def get(self, request, *args, **kwargs):

        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if not integration.is_enabled:
            raise BadRequest( 'ZoneMinder is not enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration,
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        context = {
            'integration_metadata': ZmMetaData,
            'integration_attribute_formset': integration_attribute_formset,
        }
        return render( request, 'zoneminder/panes/manage.html', context )


class ZmSettingsView( View, IntegrationHelperMixin ):

    def post(self, request, *args, **kwargs):

        integration = self.get_or_create_integration(
            integration_metadata = ZmMetaData,
        )
        if not integration.is_enabled:
            raise BadRequest( 'ZoneMinder not is enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration,
        )
        if not integration_attribute_formset.is_valid():
            context = {
                'integration_attribute_formset': integration_attribute_formset,
            }
            template = get_template( 'zoneminder/panes/zm_setings.html' )
            content = template.render( context, request = request )
            return antinode.response(
                insert_map = {
                    DIVID['INTEGRATION_SETTINGS_PANE']: content,
                },
            )
            
        with transaction.atomic():
            integration_attribute_formset.save()

        return antinode.refresh_response()
    
    
class ZmSyncView( View ):

    def post(self, request, *args, **kwargs):

        processing_result = ZoneMinderManager().sync()
        
        context = {
            'integration_metadata': ZmMetaData,
            'processing_result': processing_result,
        }
        return render( request, 'zoneminder/panes/manage.html', context )
    

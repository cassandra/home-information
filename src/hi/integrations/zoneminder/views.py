from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.attribute.enums import AttributeType

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.forms import IntegrationAttributeFormSet
from hi.integrations.core.models import Integration, IntegrationAttribute

from hi.views import bad_request_response

from .enums import ZmAttributeName
from .zm_manager import ZoneMinderManager


class ZmEnableView( View ):

    def get(self, request, *args, **kwargs):
        
        integration = self.get_or_create_integration()
        if integration.is_enabled:
            return bad_request_response( request, message = 'ZoneMinder is already enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration,
            form_kwargs = { 'is_editable': True },
        )
        return self.get_modal_response(
            request = request,
            integration_attribute_formset = integration_attribute_formset,
        )

    def post(self, request, *args, **kwargs):

        integration = self.get_or_create_integration()

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

        # TODO:
        # Check if have all needed properties
        # If not, render form for entering with button to activate




        
        raise NotImplementedError('FORCED')


        integration_attribute_formset.save()
    
        context = {
        }
        return render( request, 'zoneminder/panes/activate.html', context )

    def get_or_create_integration( self ):
        try:
            return Integration.objects.get(
                integration_type_str = IntegrationType.ZONEMINDER,
            )
        except Integration.DoesNotExist:
            pass

        with transaction.atomic():
            integration = Integration.objects.create(
                integration_type_str = IntegrationType.ZONEMINDER,
                is_enabled = False,
            )
            for attribute in ZmAttributeName:
                IntegrationAttribute.objects.create(
                    integration = integration,
                    value_type_str = str(attribute.value_type),
                    name = attribute.label,
                    value = '',
                    attribute_type_str = AttributeType.PREDEFINED,
                    is_editable = attribute.is_editable,
                    is_required = attribute.is_required,
                )
                continue
        return integration

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

    def post(self, request, *args, **kwargs):

        context = {
        }
        return render( request, 'zoneminder/panes/deactivate.html', context )
    
    
class ZmManageView( View ):

    def get(self, request, *args, **kwargs):

        context = {
            'integration_type': IntegrationType.ZONEMINDER
        }
        return render( request, 'zoneminder/panes/manage.html', context )
    
    
class ZmSyncView( View ):

    def post(self, request, *args, **kwargs):

        processing_result = ZoneMinderManager().sync()
        
        context = {
            'integration_type': IntegrationType.ZONEMINDER,
            'processing_result': processing_result,
        }
        return render( request, 'zoneminder/panes/manage.html', context )
    

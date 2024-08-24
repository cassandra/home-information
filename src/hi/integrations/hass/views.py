from django.shortcuts import render
from django.views.generic import View

from hi.integrations.core.enums import IntegrationType

from .hass_manager import HassManager


class HassEnableView( View ):

    def post(self, request, *args, **kwargs):


        # TODO:
        # Check if have all needed properties
        # If not, render form for entering with button to activate
        
        context = {
        }
        return render( request, 'hass/panes/activate.html', context )

    
class HassDisableView( View ):

    def post(self, request, *args, **kwargs):

        context = {
        }
        return render( request, 'hass/panes/deactivate.html', context )
    
    
class HassManageView( View ):

    def get(self, request, *args, **kwargs):

        context = {
            'integration_type': IntegrationType.HASS
        }
        return render( request, 'hass/panes/manage.html', context )
    
    
class HassSyncView( View ):

    def post(self, request, *args, **kwargs):

        processing_result = HassManager().sync()
        
        context = {
            'integration_type': IntegrationType.HASS,
            'processing_result': processing_result,
        }
        return render( request, 'hass/panes/manage.html', context )
    

from django.shortcuts import render
from django.views.generic import View

from hi.integrations.core.enums import IntegrationType

from .zm_manager import ZoneMinderManager


class ZmEnableView( View ):

    def post(self, request, *args, **kwargs):


        # TODO:
        # Check if have all needed properties
        # If not, render form for entering with button to activate
        
        context = {
        }
        return render( request, 'zoneminder/panes/activate.html', context )

    
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
    

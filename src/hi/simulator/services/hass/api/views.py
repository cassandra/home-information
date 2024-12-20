from django.http import JsonResponse
from django.views.generic import View

from .transient_models import HassInsteonLightSwitch


class StatesView( View ):

    def get(self, request, *args, **kwargs):

        hass_device = HassInsteonLightSwitch(
            friendly_name = 'Kitchen Light',
            insteon_address = 'F0.65.D2',
        )
        return JsonResponse( hass_device.to_api_list(), safe = False )
 
    def post(self, request, *args, **kwargs):
        pass
    

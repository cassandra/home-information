from typing import List

from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from hi.apps.control.models import Controller

from .controller_manager import ControllerManager


class ControlViewMixin:

    def get_controller( self, request, *args, **kwargs ) -> Controller:
        """ Assumes there is a required controller_id in kwargs """
        try:
            controller_id = int( kwargs.get( 'controller_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid controller id.' )
        try:
            return Controller.objects.get( id = controller_id )
        except Controller.DoesNotExist:
            raise Http404( request )

    def controller_data_response( self,
                                  request                : HttpRequest,
                                  controller             : Controller,
                                  error_list             : List[ str ],
                                  override_sensor_value  : str           = None ) -> HttpResponse:

        controller_data = ControllerManager().get_controller_data(
            controller = controller,
            error_list = error_list,
        )
        if controller_data.latest_sensor_response and ( override_sensor_value is not None ):
            controller_data.latest_sensor_response.value = override_sensor_value
            
        context = {
            'controller_data': controller_data,
        }
        return render( request, 'control/panes/controller_data.html', context )

from django.shortcuts import render
from django.views.generic import View

from .simulator_manager import SimulatorManager


class HomeView( View ):

    def get(self, request, *args, **kwargs):
        simulator_manager = SimulatorManager()
        simulator_list = simulator_manager.get_simulator_list()
        current_simulator = simulator_list[0]
        context = {
            'current_simulator': current_simulator,
            'simulator_list': simulator_list,
        }
        return render( request, 'simulator/pages/home.html', context )

    
class AddDeviceView( View ):

    def get(self, request, *args, **kwargs):
        simulator_id = kwargs.get('simulator_id')
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        context = {
            'simulator': simulator,
        }
        return render( request, 'simulator/modals/add_device.html', context )

    def post(self, request, *args, **kwargs):
        simulator_id = kwargs.get('simulator_id')
        device_id = kwargs.get('device_id')
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        simulator.add_device( device_id = device_id )
        

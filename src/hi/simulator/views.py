from dataclasses import fields, MISSING

from django.core.exceptions import BadRequest
from django.http import Http404
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

    
class AddEntityView( View ):

    def get(self, request, *args, **kwargs):
        simulator_id = kwargs.get('simulator_id')
        if not simulator_id:
            raise BadRequest( 'Missing simulator id.' )
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )

        sim_entity_class_list = simulator.get_sim_entity_class_list()

        entity_fields_list = list()
        for sim_entity_class in sim_entity_class_list:
            entity_fields = [
                { 'name': f.name,
                  'type': f.type,
                  'default': None if f.default is MISSING else f.default
                 }
                for f in fields(sim_entity_class)
            ]
            entity_fields_list.append( entity_fields )
            continue
       
        context = {
            'simulator': simulator,
            'entity_fields_list': entity_fields_list,
        }
        return render( request, 'simulator/modals/add_entity.html', context )

    def post(self, request, *args, **kwargs):
        simulator_id = kwargs.get('simulator_id')
        entity_id = kwargs.get('entity_id')
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        simulator.add_entity( entity_id = entity_id )
        

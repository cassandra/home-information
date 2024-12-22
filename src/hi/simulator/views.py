from dataclasses import fields, MISSING

from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from . import forms
from .models import DbSimEntity
from .simulator_manager import SimulatorManager
from .transient_models import SimEntity
from .view_mixins import SimulatorViewMixin


class HomeView( View, SimulatorViewMixin ):

    def get(self, request, *args, **kwargs):
        simulator_manager = SimulatorManager()
        sim_profile_list = simulator_manager.get_sim_profile_list()
        current_sim_profile = simulator_manager.current_sim_profile
        simulator_list = simulator_manager.get_simulator_list()
        current_simulator = self.get_current_simulator(
            request = request,
            simulator_list = simulator_list,
        )
        context = {
            'sim_profile_list': sim_profile_list,
            'current_sim_profile': current_sim_profile,
            'simulator_list': simulator_list,
            'current_simulator': current_simulator,
        }
        return render( request, 'simulator/pages/home.html', context )

    
class ProfileCreateView( View ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_profile_create.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'sim_profile_form': forms.SimProfileForm()
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, *args, **kwargs):

        sim_profile_form = forms.SimProfileForm( request.POST )
        if not sim_profile_form.is_valid():
            context = {
                'sim_profile_form': sim_profile_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )

        sim_profile = sim_profile_form.save()
        sim_profile = SimulatorManager().set_sim_profile(
            sim_profile = sim_profile,
        )
        return antinode.refresh_response()
        
    
class ProfileEditView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_profile_edit.html'
    
    def get(self, request, *args, **kwargs):
        sim_profile = self.get_sim_profile( request, *args, **kwargs)
        sim_profile_form = forms.SimProfileForm( instance = sim_profile )
        context = {
            'sim_profile_form': sim_profile_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, *args, **kwargs):
        sim_profile = self.get_sim_profile( request, *args, **kwargs)
        sim_profile_form = forms.SimProfileForm( request.POST, instance = sim_profile )
        if not sim_profile_form.is_valid():
            context = {
                'sim_profile_form': sim_profile_form
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )

        sim_profile = sim_profile_form.save()
        SimulatorManager().set_sim_profile( sim_profile = sim_profile )
        return antinode.refresh_response()
        
    
class ProfileSwitchView( View, SimulatorViewMixin ):

    def get(self, request, *args, **kwargs):
        sim_profile = self.get_sim_profile( request, *args, **kwargs)
        SimulatorManager().set_sim_profile(
            sim_profile = sim_profile,
        )
        url = reverse( 'simulator_home' )
        return HttpResponseRedirect( url )

    
class ProfileDeleteView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_profile_delete.html'
    
    def get(self, request, *args, **kwargs):
        sim_profile = self.get_sim_profile( request, *args, **kwargs)
        sim_entity_count = DbSimEntity.objects.filter( sim_profile = sim_profile ).count()
        context = {
            'sim_profile': sim_profile,
            'sim_entity_count': sim_entity_count,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, *args, **kwargs):
        sim_profile = self.get_sim_profile( request, *args, **kwargs)
        needs_switch = bool( sim_profile == SimulatorManager().current_sim_profile )
        sim_profile.delete()
        if needs_switch:
            sim_profile = SimulatorManager().set_sim_profile( sim_profile = None )
        return antinode.refresh_response()

    
class AddEntityView( View ):

    def get(self, request, *args, **kwargs):
        simulator_id = kwargs.get('simulator_id')
        if not simulator_id:
            raise BadRequest( 'Missing simulator id.' )
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )

        sim_entity_class_list = simulator.get_sim_entity_class_list()

        base_field_names = { f.name for f in fields(SimEntity) }
        entity_fields_list = list()
        for sim_entity_class in sim_entity_class_list:
            entity_fields = [
                { 'name': f.name,
                  'type': f.type,
                  'default': None if f.default is MISSING else f.default
                  }
                for f in fields(sim_entity_class) if f.name not in base_field_names
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

        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        simulator.add_entity( entity_id = entity_id )
        

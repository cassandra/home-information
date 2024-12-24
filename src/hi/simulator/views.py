from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from . import forms
from .models import DbSimEntity
from .simulator_manager import SimulatorManager
from .transient_models import SimEntity, SimEntityClassWrapper
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

    
class AddEntityView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/add_entity.html'
    
    def get( self, request, *args, **kwargs ):
        simulator = self.get_simulator( request, *args, **kwargs)
        sim_entity_class = self.get_entity_class( simulator, request, *args, **kwargs )
        sim_entity_class_wrapper = SimEntityClassWrapper( sim_entity_class = sim_entity_class )
        
        sim_entity_form = forms.SimEntityForm( sim_entity_class = sim_entity_class )
        context = {
            'simulator': simulator,
            'sim_entity_class_wrapper': sim_entity_class_wrapper,
            'sim_entity_form': sim_entity_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, *args, **kwargs ):
        simulator = self.get_simulator( request, *args, **kwargs)
        sim_entity_class = self.get_entity_class( simulator, request, *args, **kwargs )
        sim_entity_class_wrapper = SimEntityClassWrapper( sim_entity_class = sim_entity_class )
        
        sim_entity_form = forms.SimEntityForm(
            sim_entity_class, 
            request.POST,
        )
        if not sim_entity_form.is_valid():
            context = {
                'simulator': simulator,
                'sim_entity_class_wrapper': sim_entity_class_wrapper,
                'sim_entity_form': sim_entity_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )

        cleaned_data = sim_entity_form.clean()
        print( f'\n\nCLEANED = {cleaned_data}' )
        sim_entity = SimEntity.from_form_data( form_data = cleaned_data )
        SimulatorManager().add_sim_entity(
            simulator = simulator,
            sim_entity = sim_entity,
        )
        
        return antinode.refresh_response()

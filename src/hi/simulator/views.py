from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from .exceptions import SimEntityValidationError
from . import forms
from .models import DbSimEntity
from .simulator_manager import SimulatorManager
from .transient_models import SimEntity, SimEntityClassData
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

    
class SimEntityAddView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_entity_add.html'
    
    def get( self, request, *args, **kwargs ):
        simulator = self.get_simulator( request, *args, **kwargs)
        sim_entity_class_data = self.get_entity_class_data( simulator, request, *args, **kwargs )
        sim_entity_form = forms.SimEntityForm( sim_entity_class = sim_entity_class_data.sim_entity_class )
        context = {
            'simulator': simulator,
            'sim_entity_class_data': sim_entity_class_data,
            'sim_entity_form': sim_entity_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, *args, **kwargs ):
        simulator = self.get_simulator( request, *args, **kwargs)
        sim_entity_class_data = self.get_entity_class_data( simulator, request, *args, **kwargs )
        sim_entity_form = forms.SimEntityForm(
            sim_entity_class_data.sim_entity_class, 
            request.POST,
        )
        if not sim_entity_form.is_valid():
            context = {
                'simulator': simulator,
                'sim_entity_class_data': sim_entity_class_data,
                'sim_entity_form': sim_entity_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )

        cleaned_data = sim_entity_form.clean()
        sim_entity = SimEntity.from_form_data( form_data = cleaned_data )
        try:
            SimulatorManager().add_sim_entity(
                simulator = simulator,
                sim_entity = sim_entity,
            )
        except SimEntityValidationError as ve:
            raise BadRequest( str(ve) )
        return antinode.refresh_response()

    
class SimEntityEditView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_entity_edit.html'

    def get( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = SimulatorManager().get_simulator( simulator_id = db_sim_entity.simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )
        sim_entity_class_data = self.get_entity_class_data_by_id(
            simulator = simulator,
            class_id = db_sim_entity.entity_class_id,
        )
        sim_entity = SimEntity.from_json_dict( db_sim_entity.editable_fields )
        sim_entity_form = forms.SimEntityForm(
            sim_entity_class = sim_entity_class_data.sim_entity_class,
            initial = sim_entity.to_initial_form_values(),
        )
        context = {
            'simulator': simulator,
            'db_sim_entity': db_sim_entity,
            'sim_entity': sim_entity,
            'sim_entity_form': sim_entity_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = SimulatorManager().get_simulator( simulator_id = db_sim_entity.simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )
        sim_entity_class_data = self.get_entity_class_data_by_id(
            simulator = simulator,
            class_id = db_sim_entity.entity_class_id,
        )
        previous_sim_entity = SimEntity.from_json_dict( db_sim_entity.editable_fields )
        sim_entity_form = forms.SimEntityForm(
            sim_entity_class_data.sim_entity_class, 
            request.POST,
        )
        if not sim_entity_form.is_valid():
            context = {
                'simulator': simulator,
                'db_sim_entity': db_sim_entity,
                'sim_entity': previous_sim_entity,
                'sim_entity_form': sim_entity_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )

        cleaned_data = sim_entity_form.clean()
        sim_entity = SimEntity.from_form_data( form_data = cleaned_data )
        try:
            SimulatorManager().update_sim_entity(
                db_sim_entity = db_sim_entity,
                sim_entity = sim_entity,
            )
        except SimEntityValidationError as ve:
            raise BadRequest( str(ve) )
        return antinode.refresh_response()
    
    
class SimEntityDeleteView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_entity_delete.html'
    
    def get( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        context = {
            'db_sim_entity': db_sim_entity,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )
    
    def post( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        SimulatorManager().delete_sim_entity(
            db_sim_entity = db_sim_entity,
        )
        return antinode.refresh_response()

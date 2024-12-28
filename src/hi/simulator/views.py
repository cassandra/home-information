from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from .exceptions import SimEntityValidationError
from . import forms
from .models import DbSimEntity
from .simulator_manager import SimulatorManager
from .sim_entity import SimEntity
from .view_mixins import SimulatorViewMixin


class HomeView( View, SimulatorViewMixin ):

    def get(self, request, *args, **kwargs):
        simulator_manager = SimulatorManager()
        sim_profile_list = simulator_manager.sim_profile_list
        current_sim_profile = simulator_manager.current_sim_profile
        simulator_data_list = simulator_manager.get_simulator_data_list()
        current_simulator = self.get_current_simulator(
            request = request,
            simulator_list = [ x.simulator for x in simulator_data_list ],
        )
        context = {
            'sim_profile_list': sim_profile_list,
            'current_sim_profile': current_sim_profile,
            'simulator_data_list': simulator_data_list,
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
        sim_entity_definition = self.get_entity_definition( simulator, request, *args, **kwargs )
        sim_entity_fields_form = forms.SimEntityFieldsForm( sim_entity_definition.sim_entity_fields_class )
        context = {
            'simulator': simulator,
            'sim_entity_definition': sim_entity_definition,
            'sim_entity_fields_form': sim_entity_fields_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, *args, **kwargs ):
        simulator = self.get_simulator( request, *args, **kwargs)
        sim_entity_definition = self.get_entity_definition( simulator, request, *args, **kwargs )
        sim_entity_fields_form = forms.SimEntityFieldsForm(
            sim_entity_definition.sim_entity_fields_class,
            request.POST,
        )

        def error_response():
            context = {
                'simulator': simulator,
                'sim_entity_definition': sim_entity_definition,
                'sim_entity_fields_form': sim_entity_fields_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )
        
        if not sim_entity_fields_form.is_valid():
            return error_response()

        cleaned_data = sim_entity_fields_form.clean()
        SimEntityFieldsSubclass = sim_entity_definition.sim_entity_fields_class
        sim_entity_fields = SimEntityFieldsSubclass.from_form_data( form_data = cleaned_data )
        try:
            SimulatorManager().add_sim_entity(
                simulator = simulator,
                sim_entity_definition = sim_entity_definition,
                sim_entity_fields = sim_entity_fields,
            )
            return antinode.refresh_response()

        except SimEntityValidationError as ve:
            sim_entity_fields_form.add_error( None, str(ve) )
            return error_response()

    
class SimEntityEditView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_entity_edit.html'

    def get( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = self.get_simulator_by_id( simulator_id = db_sim_entity.simulator_id )
        sim_entity_definition = self.get_entity_definition_by_id(
            simulator = simulator,
            class_id = db_sim_entity.entity_fields_class_id,
        )
        sim_entity = SimEntity(
            db_sim_entity = db_sim_entity,
            sim_entity_definition = sim_entity_definition,
        )
        sim_entity_fields_form = forms.SimEntityFieldsForm(
            sim_entity_fields_class = sim_entity_definition.sim_entity_fields_class,
            initial = sim_entity.sim_entity_fields.to_initial_form_values(),
        )
        context = {
            'simulator': simulator,
            'db_sim_entity': db_sim_entity,
            'sim_entity_fields_form': sim_entity_fields_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = self.get_simulator_by_id( simulator_id = db_sim_entity.simulator_id )
        sim_entity_definition = self.get_entity_definition_by_id(
            simulator = simulator,
            class_id = db_sim_entity.entity_fields_class_id,
        )
        sim_entity_fields_form = forms.SimEntityFieldsForm(
            sim_entity_definition.sim_entity_fields_class, 
            request.POST,
        )

        def error_response():
            context = {
                'simulator': simulator,
                'db_sim_entity': db_sim_entity,
                'sim_entity_fields_form': sim_entity_fields_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )
            
        if not sim_entity_fields_form.is_valid():
            return error_response()
        
        cleaned_data = sim_entity_fields_form.clean()
        SimEntityFieldsSubclass = sim_entity_definition.sim_entity_fields_class
        sim_entity_fields = SimEntityFieldsSubclass.from_form_data( form_data = cleaned_data )

        try:
            SimulatorManager().update_sim_entity_fields(
                simulator = simulator,
                sim_entity_definition= sim_entity_definition,
                db_sim_entity = db_sim_entity,
                sim_entity_fields = sim_entity_fields,
            )
            return antinode.refresh_response()
        
        except SimEntityValidationError as ve:
            sim_entity_fields_form.add_error( None, str(ve) )
            return error_response()
    
    
class SimEntityDeleteView( View, SimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_entity_delete.html'
    
    def get( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = self.get_simulator_by_id( simulator_id = db_sim_entity.simulator_id )
        sim_entity_definition = self.get_entity_definition_by_id(
            simulator = simulator,
            class_id = db_sim_entity.entity_fields_class_id,
        )
        sim_entity = SimEntity(
            db_sim_entity = db_sim_entity,
            sim_entity_definition = sim_entity_definition,
        )
        context = {
            'sim_entity': sim_entity,
            'sim_entity_field': sim_entity.sim_entity_fields,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )
    
    def post( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = self.get_simulator_by_id( simulator_id = db_sim_entity.simulator_id )
        SimulatorManager().delete_sim_entity(
            simulator = simulator,
            db_sim_entity = db_sim_entity,
        )
        return antinode.refresh_response()

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from .enums import SimulatorFaultMode
from .exceptions import SimEntityValidationError
from . import forms
from .models import DbSimEntity, SimProfile
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
            'fault_mode_choices': list( SimulatorFaultMode ),
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
        
    
class ProfileCloneView( View, SimulatorViewMixin ):
    """
    Clone the current profile into a new profile with operator-
    chosen name. The clone copies the profile row and every
    DbSimEntity row beneath it; SimState values are not persisted
    (rebuilt from class defaults on every profile load), so the
    clone naturally gets fresh state semantics with no extra work.

    The new profile becomes the active profile after creation —
    matches the Create flow's behavior and gives the operator
    immediate visual confirmation in the simulator UI.
    """

    MODAL_TEMPLATE_NAME = 'simulator/modals/sim_profile_clone.html'

    def get(self, request, *args, **kwargs):
        source_profile = self.get_sim_profile( request, *args, **kwargs )
        suggested_name = self._suggest_name( source_profile.name )
        sim_profile_form = forms.SimProfileForm(
            initial = { 'name': suggested_name },
        )
        context = {
            'source_profile': source_profile,
            'sim_profile_form': sim_profile_form,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, *args, **kwargs):
        source_profile = self.get_sim_profile( request, *args, **kwargs )
        sim_profile_form = forms.SimProfileForm( request.POST )
        if not sim_profile_form.is_valid():
            context = {
                'source_profile': source_profile,
                'sim_profile_form': sim_profile_form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )

        new_name = sim_profile_form.cleaned_data['name']
        with transaction.atomic():
            new_profile = SimulatorManager.clone_sim_profile(
                source_profile = source_profile,
                new_name = new_name,
            )
        SimulatorManager().set_sim_profile( sim_profile = new_profile )
        return antinode.refresh_response()

    @staticmethod
    def _suggest_name( source_name : str ) -> str:
        """Default new-name suggestion: '<source> (copy)'.

        If that name is already taken, append a numeric suffix
        ('<source> (copy 2)', '(copy 3)', ...) until a free name
        is found. Bounded probe — no DB-side lock — because the
        unique-name constraint at submit time is the actual
        guard; this is just a friendly default, and a race here
        means the operator sees a 'name already exists' on submit
        and edits the field, which is acceptable."""
        candidate = f'{source_name} (copy)'
        if not SimProfile.objects.filter( name = candidate ).exists():
            return candidate
        for index in range( 2, 100 ):
            candidate = f'{source_name} (copy {index})'
            if not SimProfile.objects.filter( name = candidate ).exists():
                return candidate
        return f'{source_name} (copy)'


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


class SetSimulatorFaultModeView( View, SimulatorViewMixin ):
    """
    Operator-driven control to flip a simulator into a fault-injection
    mode (or back to HEALTHY). Lives at a top-level URL — outside the
    /services/<short_name>/ subtree — so the fault-injection middleware
    never intercepts requests to it. This is the operator's escape hatch
    when a simulator is in any non-HEALTHY mode.

    Returns the fault-mode form HTML fragment so antinode.js can swap it
    in place (data-async + data-mode=replace), avoiding a full page
    reload on each toggle.
    """

    TEMPLATE_NAME = 'simulator/panes/fault_mode_form.html'

    def post( self, request, *args, **kwargs ):
        simulator = self.get_simulator_by_id(
            simulator_id = kwargs.get('simulator_id'),
        )
        fault_mode_name = request.POST.get('fault_mode')
        try:
            fault_mode = SimulatorFaultMode[ fault_mode_name ]
        except (KeyError, TypeError):
            raise BadRequest( f'Invalid fault mode: {fault_mode_name}' )
        simulator.set_fault_mode( fault_mode )
        context = {
            'simulator': simulator,
            'fault_mode_choices': list( SimulatorFaultMode ),
        }
        return render( request, self.TEMPLATE_NAME, context )


class SimStateSetView( View, SimulatorViewMixin ):

    TEMPLATE_NAME = 'simulator/panes/sim_state.html'

    def post( self, request, *args, **kwargs ):
        simulator = self.get_simulator( request, *args, **kwargs)
        sim_entity_id = int( kwargs.get( 'sim_entity_id' ))
        sim_state_id = kwargs.get( 'sim_state_id' )
        value_str = request.POST.get('value')
        sim_state = simulator.set_sim_state(
            sim_entity_id = sim_entity_id,
            sim_state_id = sim_state_id,
            value_str = value_str,
        )
        context = {
            'sim_state': sim_state,
        }
        return render( request, self.TEMPLATE_NAME, context )
        

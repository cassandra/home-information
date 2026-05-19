from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.simulator.settings.enums import SimTemperatureUnit
from hi.simulator.settings.runtime_settings import SimulatorRuntimeSettings

from .enums import ServiceFaultMode
from .exceptions import SimEntityValidationError
from . import forms
from .models import DbSimEntity, SimProfile
from .service_simulator_manager import ServiceSimulatorManager
from .sim_entity import SimEntity
from .view_mixins import ServiceSimulatorViewMixin


class ServicesView( View, ServiceSimulatorViewMixin ):

    def get(self, request, *args, **kwargs):
        simulator_manager = ServiceSimulatorManager()
        sim_profile_list = simulator_manager.sim_profile_list
        current_sim_profile = simulator_manager.current_sim_profile
        simulator_data_list = simulator_manager.get_simulator_data_list()
        current_simulator = self.get_current_simulator(
            request = request,
            simulator_list = [ x.simulator for x in simulator_data_list ],
        )
        runtime_settings = SimulatorRuntimeSettings()
        context = {
            'active_section': 'services',
            'sim_profile_list': sim_profile_list,
            'current_sim_profile': current_sim_profile,
            'simulator_data_list': simulator_data_list,
            'current_simulator': current_simulator,
            'fault_mode_choices': list( ServiceFaultMode ),
            'temperature_unit_choices': list( SimTemperatureUnit ),
            'temperature_unit_override': runtime_settings.temperature_unit_override,
        }
        return render( request, 'services/pages/services.html', context )


class SimStatesView( View ):
    """Periodic-poll endpoint returning a flat map of every service
    simulator state's current value, keyed by the same DOM id used in
    sim_state.html so the client can update in place."""

    def get(self, request, *args, **kwargs):
        states = {}
        simulator_data_list = ServiceSimulatorManager().get_simulator_data_list()
        for simulator_data in simulator_data_list:
            simulator = simulator_data.simulator
            for sim_entity in simulator.sim_entities:
                for sim_state in sim_entity.sim_state_list:
                    key = (
                        f'hi-sim-state-{sim_state.simulator_id}'
                        f'-{sim_state.sim_entity_id}'
                        f'-{sim_state.sim_state_id}'
                    )
                    states[key] = str( sim_state.value )
        return JsonResponse( { 'states': states } )


class ProfileCreateView( View ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_profile_create.html'

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
        sim_profile = ServiceSimulatorManager().set_sim_profile(
            sim_profile = sim_profile,
        )
        return antinode.refresh_response()


class ProfileEditView( View, ServiceSimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_profile_edit.html'

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
        ServiceSimulatorManager().set_sim_profile( sim_profile = sim_profile )
        return antinode.refresh_response()


class ProfileCloneView( View, ServiceSimulatorViewMixin ):
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

    MODAL_TEMPLATE_NAME = 'services/modals/sim_profile_clone.html'

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
            new_profile = ServiceSimulatorManager.clone_sim_profile(
                source_profile = source_profile,
                new_name = new_name,
            )
        ServiceSimulatorManager().set_sim_profile( sim_profile = new_profile )
        return antinode.refresh_response()

    @staticmethod
    def _suggest_name( source_name : str ) -> str:
        candidate = f'{source_name} (copy)'
        if not SimProfile.objects.filter( name = candidate ).exists():
            return candidate
        for index in range( 2, 100 ):
            candidate = f'{source_name} (copy {index})'
            if not SimProfile.objects.filter( name = candidate ).exists():
                return candidate
        return f'{source_name} (copy)'


class ProfileSwitchView( View, ServiceSimulatorViewMixin ):

    def get(self, request, *args, **kwargs):
        sim_profile = self.get_sim_profile( request, *args, **kwargs)
        ServiceSimulatorManager().set_sim_profile(
            sim_profile = sim_profile,
        )
        url = reverse( 'simulator_home' )
        return HttpResponseRedirect( url )


class ProfileDeleteView( View, ServiceSimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_profile_delete.html'

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
        needs_switch = bool( sim_profile == ServiceSimulatorManager().current_sim_profile )
        sim_profile.delete()
        if needs_switch:
            sim_profile = ServiceSimulatorManager().set_sim_profile( sim_profile = None )
        return antinode.refresh_response()


class SimEntityAddView( View, ServiceSimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_entity_add.html'

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
            ServiceSimulatorManager().add_sim_entity(
                simulator = simulator,
                sim_entity_definition = sim_entity_definition,
                sim_entity_fields = sim_entity_fields,
            )
            return antinode.refresh_response()

        except SimEntityValidationError as ve:
            sim_entity_fields_form.add_error( None, str(ve) )
            return error_response()


class SimEntityEditView( View, ServiceSimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_entity_edit.html'

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
            ServiceSimulatorManager().update_sim_entity_fields(
                simulator = simulator,
                sim_entity_definition= sim_entity_definition,
                db_sim_entity = db_sim_entity,
                sim_entity_fields = sim_entity_fields,
            )
            return antinode.refresh_response()

        except SimEntityValidationError as ve:
            sim_entity_fields_form.add_error( None, str(ve) )
            return error_response()


class SimEntityDeleteView( View, ServiceSimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_entity_delete.html'

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
        ServiceSimulatorManager().delete_sim_entity(
            simulator = simulator,
            db_sim_entity = db_sim_entity,
        )
        return antinode.refresh_response()


class SetServiceFaultModeView( View, ServiceSimulatorViewMixin ):
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

    TEMPLATE_NAME = 'services/panes/fault_mode_form.html'

    def post( self, request, *args, **kwargs ):
        simulator = self.get_simulator_by_id(
            simulator_id = kwargs.get('simulator_id'),
        )
        fault_mode_name = request.POST.get('fault_mode')
        try:
            fault_mode = ServiceFaultMode[ fault_mode_name ]
        except (KeyError, TypeError):
            raise BadRequest( f'Invalid fault mode: {fault_mode_name}' )
        simulator.set_fault_mode( fault_mode )
        context = {
            'simulator': simulator,
            'fault_mode_choices': list( ServiceFaultMode ),
        }
        return render( request, self.TEMPLATE_NAME, context )


class SimStateSetView( View, ServiceSimulatorViewMixin ):

    TEMPLATE_NAME = 'services/panes/sim_state.html'

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

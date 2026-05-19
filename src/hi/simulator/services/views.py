from django.core.exceptions import BadRequest
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.settings.enums import SimTemperatureUnit
from hi.simulator.settings.runtime_settings import SimulatorRuntimeSettings

from .enums import ServiceFaultMode
from .exceptions import SimEntityValidationError
from . import forms
from .service_simulator_manager import ServiceSimulatorManager
from .sim_entity import SimEntity
from .view_mixins import ServiceSimulatorViewMixin


def _build_simulator_tab_contexts():
    """Per-simulator render context for the services tabbed page.
    Bundles each ServiceSimulator with the profile data its tab needs
    (current profile + dropdown options), so the template can
    iterate without consulting ProfileManager itself.
    """
    profile_manager = ProfileManager()
    tab_contexts = []
    for sim_data in ServiceSimulatorManager().get_simulator_data_list():
        simulator = sim_data.simulator
        tab_contexts.append({
            'simulator_data': sim_data,
            'simulator': simulator,
            'module_key': simulator.module_key,
            'module_label': simulator.label,
            'profile_list': profile_manager.list_profiles( simulator.module_key ),
            'current_profile': profile_manager.get_current( simulator.module_key ),
        })
        continue
    return tab_contexts


class ServicesView( View, ServiceSimulatorViewMixin ):

    def get(self, request, *args, **kwargs):
        tab_contexts = _build_simulator_tab_contexts()
        current_simulator = self.get_current_simulator(
            request = request,
            simulator_list = [ tc[ 'simulator' ] for tc in tab_contexts ],
        )
        runtime_settings = SimulatorRuntimeSettings()
        context = {
            'active_section': 'services',
            'tab_contexts': tab_contexts,
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
        simulator = self._get_simulator_for_entity( db_sim_entity )
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
        simulator = self._get_simulator_for_entity( db_sim_entity )
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

    def _get_simulator_for_entity( self, db_sim_entity ):
        """The DbSimEntity row is tied to a SimProfile (with
        module_key) — derive the owning simulator by matching
        module_key against the discovered service simulators."""
        module_key = db_sim_entity.sim_profile.module_key
        for sim_data in ServiceSimulatorManager().get_simulator_data_list():
            if sim_data.simulator.module_key == module_key:
                return sim_data.simulator
            continue
        raise BadRequest(
            f'No service simulator registered for module {module_key!r}'
        )


class SimEntityDeleteView( View, ServiceSimulatorViewMixin ):

    MODAL_TEMPLATE_NAME = 'services/modals/sim_entity_delete.html'

    def get( self, request, *args, **kwargs ):
        db_sim_entity = self.get_db_sim_entity( request, *args, **kwargs )
        simulator = self._get_simulator_for_entity( db_sim_entity )
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
        simulator = self._get_simulator_for_entity( db_sim_entity )
        ServiceSimulatorManager().delete_sim_entity(
            simulator = simulator,
            db_sim_entity = db_sim_entity,
        )
        return antinode.refresh_response()

    def _get_simulator_for_entity( self, db_sim_entity ):
        module_key = db_sim_entity.sim_profile.module_key
        for sim_data in ServiceSimulatorManager().get_simulator_data_list():
            if sim_data.simulator.module_key == module_key:
                return sim_data.simulator
            continue
        raise BadRequest(
            f'No service simulator registered for module {module_key!r}'
        )


class SetServiceFaultModeView( View, ServiceSimulatorViewMixin ):
    """Operator-driven control to flip a simulator into a fault-
    injection mode (or back to HEALTHY). Lives at a top-level URL —
    outside the /services/<short_name>/ subtree — so the fault-
    injection middleware never intercepts requests to it. This is the
    operator's escape hatch when a simulator is in any non-HEALTHY
    mode.

    Returns the fault-mode form HTML fragment so antinode.js can swap
    it in place (data-async + data-mode=replace), avoiding a full
    page reload on each toggle.
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

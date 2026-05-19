from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from .enums import SimTemperatureUnit
from .runtime_settings import SimulatorRuntimeSettings


class SettingsView( View ):

    def get(self, request, *args, **kwargs):
        context = { 'active_section': 'settings' }
        return render( request, 'settings/pages/settings.html', context )


class TemperatureUnitOverrideSetView( View ):
    """Operator control to flip the simulator's process-wide
    temperature unit override (or clear it back to per-profile
    defaults). Returns the dropdown's form fragment so antinode.js
    can swap it in place — preserves the current integration tab
    and avoids a full reload."""

    TEMPLATE_NAME = 'settings/panes/temperature_unit_override_form.html'

    def post( self, request, *args, **kwargs ):
        raw = ( request.POST.get( 'temperature_unit' ) or '' ).strip()
        if raw:
            override = SimTemperatureUnit.from_name_safe( raw )
            if override is None:
                raise BadRequest( f'Unknown temperature unit: {raw!r}' )
        else:
            override = None
        SimulatorRuntimeSettings().set_temperature_unit_override( override )
        context = {
            'temperature_unit_choices': list( SimTemperatureUnit ),
            'temperature_unit_override': override,
        }
        return render( request, self.TEMPLATE_NAME, context )

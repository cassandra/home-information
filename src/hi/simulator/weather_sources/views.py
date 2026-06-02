from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from hi.simulator.fault_injection import FaultMode
from hi.simulator.profile.profile_manager import ProfileManager

from .fault_state import get_fault_mode, set_fault_mode
from .registry import get_weather_source_data_list

FAULT_MODE_TEMPLATE = 'weather_sources/panes/fault_mode_form.html'


def _fault_mode_context( short_name : str ) -> dict:
    return {
        'short_name': short_name,
        'current': get_fault_mode( short_name ),
        'choices': list( FaultMode ),
    }


def _build_weather_tab_specs( active_short_name : str ):
    """Tab strip data for the Weather section. Each entry routes to
    its own URL (``simulator_weather_source``)."""
    specs = []
    for source_data in get_weather_source_data_list():
        specs.append({
            'label': source_data.label,
            'url': reverse( 'simulator_weather_source',
                            kwargs = { 'short_name': source_data.short_name } ),
            'is_active': ( source_data.short_name == active_short_name ),
        })
        continue
    return specs


class WeatherIndexView( View ):
    """Default ``/weather/`` route — redirects to the first registered
    weather source's per-tab URL."""

    def get(self, request, *args, **kwargs):
        source_data_list = get_weather_source_data_list()
        if not source_data_list:
            return render( request, 'weather_sources/pages/empty.html',
                           { 'active_section': 'weather',
                             'tab_specs': [] } )
        first = source_data_list[0]
        return HttpResponseRedirect(
            reverse( 'simulator_weather_source',
                     kwargs = { 'short_name': first.short_name } )
        )


class WeatherSourceView( View ):
    """Renders a single weather source's tab body."""

    def get(self, request, short_name, *args, **kwargs):
        source_data = next(
            ( s for s in get_weather_source_data_list()
              if s.short_name == short_name ),
            None,
        )
        if source_data is None:
            raise Http404( f'Unknown weather source: {short_name!r}' )

        profile_manager = ProfileManager()
        context = {
            'active_section': 'weather',
            'tab_specs': _build_weather_tab_specs(
                active_short_name = source_data.short_name,
            ),
            'source_data': source_data,
            'module': {
                'module_key': source_data.module_key,
                'label': source_data.label,
            },
            'profile_list': profile_manager.list_profiles( source_data.module_key ),
            'current_profile': profile_manager.get_current( source_data.module_key ),
        }
        return render( request, 'weather_sources/pages/source.html', context )


class WeatherFaultModeSetView( View ):
    """Auto-submit target for a source's inline fault-mode dropdown. Sets
    the in-memory mode and re-renders the fragment for in-place swap."""

    def post(self, request, short_name, *args, **kwargs):
        known = { s.short_name for s in get_weather_source_data_list() }
        if short_name not in known:
            raise Http404( f'Unknown weather source: {short_name!r}' )

        fault_mode_name = request.POST.get( 'fault_mode' )
        try:
            fault_mode = FaultMode[ fault_mode_name ]
        except KeyError:
            raise BadRequest( f'Invalid fault mode: {fault_mode_name}' )

        set_fault_mode( short_name, fault_mode )
        return render( request, FAULT_MODE_TEMPLATE, _fault_mode_context( short_name ) )

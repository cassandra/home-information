from django.shortcuts import render
from django.views.generic import View

from hi.simulator.profile.profile_manager import ProfileManager

from .registry import get_weather_source_data_list


class WeatherView( View ):

    def get(self, request, *args, **kwargs):
        profile_manager = ProfileManager()
        tab_contexts = []
        for source_data in get_weather_source_data_list():
            tab_contexts.append({
                'source_data': source_data,
                'module_key': source_data.module_key,
                'label': source_data.label,
                'short_name': source_data.short_name,
                'tab_template': source_data.tab_template,
                'profile_list': profile_manager.list_profiles( source_data.module_key ),
                'current_profile': profile_manager.get_current( source_data.module_key ),
            })
            continue
        context = {
            'active_section': 'weather',
            'tab_contexts': tab_contexts,
        }
        return render( request, 'weather_sources/pages/weather.html', context )

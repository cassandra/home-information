from django.shortcuts import render
from django.views.generic import View

from .registry import get_weather_source_data_list


class WeatherView( View ):

    def get(self, request, *args, **kwargs):
        weather_source_data_list = get_weather_source_data_list()
        context = {
            'active_section': 'weather',
            'weather_source_data_list': weather_source_data_list,
        }
        return render( request, 'weather_sources/pages/weather.html', context )

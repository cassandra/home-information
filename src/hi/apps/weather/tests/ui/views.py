from django.shortcuts import render
from django.views.generic import View

from hi.apps.weather.tests.synthetic_data import WeatherSyntheticData


class TestUiWeatherHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'weather_overview_data': WeatherSyntheticData.WeatherOverviewData_001,
        }
        return render(request, "weather/tests/ui/home.html", context )


class TestUiConditionsDetailsView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'weather_conditions_data': WeatherSyntheticData.WeatherConditionsData_001,
        }
        return render(request, "weather/modals/conditions_details.html", context )


class TestUiAstronomicalDetailsView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'daily_astronomical_data': WeatherSyntheticData.DailyAstronomicalData_001,
        }
        return render(request, "weather/modals/astronomical_details.html", context )


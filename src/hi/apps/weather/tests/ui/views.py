from django.shortcuts import render
from django.views.generic import View

from hi.apps.weather.tests.synthetic_data import WeatherSyntheticData


class TestUiWeatherHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'weather_overview_data': WeatherSyntheticData.get_random_weather_overview_data(),
        }
        return render(request, "weather/tests/ui/home.html", context )


class TestUiConditionsDetailsView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'weather_conditions_data': WeatherSyntheticData.get_random_weather_conditions_data(),
        }
        return render(request, "weather/modals/conditions_details.html", context )


class TestUiAstronomicalDetailsView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'daily_astronomical_data': WeatherSyntheticData.get_random_daily_astronomical_data(),
        }
        return render(request, "weather/modals/astronomical_details.html", context )


class TestUiForecastView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'hourly_forecast_data_list': WeatherSyntheticData.get_random_hourly_forecast_data_list(),
            'daily_forecast_data_list': WeatherSyntheticData.get_random_daily_forecast_data_list(),
        }
        return render(request, "weather/modals/forecast.html", context )


class TestUiRadarView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "weather/modals/radar.html", context )


class TestUiHistoryView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'daily_history_data_list': WeatherSyntheticData.get_random_daily_history_data_list(),
        }
        return render(request, "weather/modals/history.html", context )


from django.shortcuts import render
from django.views.generic import View

from hi.apps.weather.tests.synthetic_data import WeatherSyntheticData


class TestUiWeatherHomeView( View ):

    def get(self, request, *args, **kwargs):
        weather_overview_data = WeatherSyntheticData.get_random_weather_overview_data()
        context = {
            'weather_overview_data': weather_overview_data,
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
            'interval_hourly_forecast_list': WeatherSyntheticData.get_random_interval_hourly_forecast_list(),
            'interval_daily_forecast_list': WeatherSyntheticData.get_random_interval_daily_forecast_list(),
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
            'interval_daily_history_list': WeatherSyntheticData.get_random_interval_daily_history_list(),
        }
        return render(request, "weather/modals/history.html", context )


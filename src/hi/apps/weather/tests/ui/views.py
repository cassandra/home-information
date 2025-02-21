from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.transient_models import (
    DailyAstronomicalData,
    WeatherConditionsData,
    WeatherDataPoint,
    WeatherOverviewData,
)
from hi.units import UnitQuantity


class TestUiWeatherHomeView( View ):

    def get(self, request, *args, **kwargs):

        now = datetimeproxy.now()
        
        conditions_current = WeatherConditionsData(
            temperature  = WeatherDataPoint(
                source = 'test',
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( 18, 'degF' ),
            ),
            
        )
        astronomical_today = DailyAstronomicalData(
        )
        weather_overview_data = WeatherOverviewData(
            conditions_current = conditions_current,
            astronomical_today = astronomical_today,
        )
        context = {
            'weather_overview_data': weather_overview_data,
        }
        return render(request, "weather/tests/ui/home.html", context )

    

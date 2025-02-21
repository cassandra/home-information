from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiWeatherHomeView.as_view(), 
             name='weather_tests_ui'),

    re_path( r'^conditions/details$',
             views.TestUiConditionsDetailsView.as_view(), 
             name='weather_tests_ui_conditions_details'),

    re_path( r'^astronomical/details$',
             views.TestUiAstronomicalDetailsView.as_view(), 
             name='weather_tests_ui_astronomical_details'),

    re_path( r'^forecast$',
             views.TestUiForecastView.as_view(), 
             name='weather_tests_ui_forecast'),

    re_path( r'^radar$',
             views.TestUiRadarView.as_view(), 
             name='weather_tests_ui_radar'),

    re_path( r'^history$',
             views.TestUiHistoryView.as_view(), 
             name='weather_tests_ui_history'),

        
]

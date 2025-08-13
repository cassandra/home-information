from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^current-conditions/details$', 
             views.CurrentConditionsDetailsView.as_view(), 
             name='weather_current_conditions_details'),

    re_path( r'^todays-astronomical/details$', 
             views.TodaysAstronomicalDetailsView.as_view(), 
             name='weather_todays_astronomical_details'),

    re_path( r'^forecast$', 
             views.ForecastView.as_view(), 
             name='weather_forecast'),

    re_path( r'^radar$', 
             views.RadarView.as_view(), 
             name='weather_radar'),

    re_path( r'^history$', 
             views.HistoryView.as_view(), 
             name='weather_history'),
]

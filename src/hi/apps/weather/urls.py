from django.urls import path

from . import views


urlpatterns = [

    path( 'current-conditions/details', 
          views.CurrentConditionsDetailsView.as_view(), 
          name='weather_current_conditions_details'),

    path( 'todays-astronomical/details', 
          views.TodaysAstronomicalDetailsView.as_view(), 
          name='weather_todays_astronomical_details'),

    path( 'forecast', 
          views.ForecastView.as_view(), 
          name='weather_forecast'),

    path( 'history',
          views.HistoryView.as_view(),
          name='weather_history'),
]

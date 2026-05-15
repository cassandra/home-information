from django.urls import path

from . import views


urlpatterns = [

    path( '',
          views.TestUiWeatherHomeView.as_view(), 
          name='weather_tests_ui'),

    path( 'conditions/details',
          views.TestUiConditionsDetailsView.as_view(), 
          name='weather_tests_ui_conditions_details'),

    path( 'astronomical/details',
          views.TestUiAstronomicalDetailsView.as_view(), 
          name='weather_tests_ui_astronomical_details'),

    path( 'forecast',
          views.TestUiForecastView.as_view(), 
          name='weather_tests_ui_forecast'),

    path( 'history',
          views.TestUiHistoryView.as_view(), 
          name='weather_tests_ui_history'),

        
]

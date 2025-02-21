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

        
]

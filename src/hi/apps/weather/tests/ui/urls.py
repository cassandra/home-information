from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiWeatherHomeView.as_view(), 
             name='weather_tests_ui'),
]

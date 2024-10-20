from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^settings$', 
             views.ConfigSettingsView.as_view(), 
             name='config_settings' ),

]

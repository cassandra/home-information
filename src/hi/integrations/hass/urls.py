
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^settings$', 
             views.HassSettingsView.as_view(), 
             name='hass_settings' ),

    re_path( r'^sync$', 
             views.HassSyncView.as_view(), 
             name='hass_sync' ),

]

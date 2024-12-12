
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^settings$', 
             views.ZmSettingsView.as_view(), 
             name='zm_settings' ),

    re_path( r'^sync$', 
             views.ZmSyncView.as_view(), 
             name='zm_sync' ),

]

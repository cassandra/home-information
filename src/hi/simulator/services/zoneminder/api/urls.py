from django.urls import re_path

from . import views

urlpatterns = [
    
    re_path( r'^host/login\.json$',
             views.HostLoginView.as_view(),
             name = 'zm_api_host_login' ),
    
    re_path( r'^host/getVersion\.json$',
             views.HostVersionView.as_view(),
             name = 'zm_api_host_version' ),

    re_path( r'^monitors\.json$',
             views.MonitorsView.as_view(),
             name = 'zm_api_monitors' ),
    
    re_path( r'^monitors/(?P<monitor_id>\d+)\.json$',
             views.MonitorsView.as_view(),
             name = 'zm_api_monitors_set' ),

    re_path( r'^states\.json$',
             views.StatesView.as_view(),
             name = 'zm_api_states' ),
    
    re_path( r'^events/index/(?P<filter>.+).json$',
             views.EventsIndexView.as_view(),
             name = 'zm_api_events_index' ),
]

from django.urls import path

from . import views

urlpatterns = [
    
    path( 'host/login.json',
          views.HostLoginView.as_view(),
          name = 'zm_api_host_login' ),
    
    path( 'host/getVersion.json',
          views.HostVersionView.as_view(),
          name = 'zm_api_host_version' ),

    path( 'monitors.json',
          views.MonitorsView.as_view(),
          name = 'zm_api_monitors' ),
    
    path( 'monitors/<int:monitor_id>.json',
          views.MonitorsView.as_view(),
          name = 'zm_api_monitors_set' ),
    
    path( 'states.json',
          views.StatesView.as_view(),
          name = 'zm_api_states' ),
    
    path( 'states/change/<path:run_state>.json',
          views.StatesChangeView.as_view(),
          name = 'zm_api_states_change' ),

    path( 'events/index/<path:filter>.json',
          views.EventsIndexView.as_view(),
          name = 'zm_api_events_index' ),
]

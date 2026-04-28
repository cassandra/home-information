from django.urls import re_path

from . import views

urlpatterns = [

    re_path( r'^$',
             views.PingView.as_view(),
             name = 'hass_api_ping' ),

    re_path( r'^states$',
             views.AllStatesView.as_view(),
             name = 'hass_api_states' ),

    re_path( r'^states/(?P<entity_id>[\w\._\-]+)$',
             views.StateView.as_view(),
             name = 'hass_api_states_set' ),

    re_path( r'^services/(?P<domain>[\w_]+)/(?P<service>[\w_]+)$',
             views.ServiceCallView.as_view(),
             name = 'hass_api_service_call' ),
]

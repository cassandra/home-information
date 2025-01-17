from django.urls import re_path

from . import views

urlpatterns = [
    
    re_path( r'^states$',
             views.AllStatesView.as_view(),
             name = 'hass_api_states' ),

    re_path( r'^states/(?P<entity_id>[\w\._\-]+)$',
             views.StateView.as_view(),
             name = 'hass_api_states_set' ),
]

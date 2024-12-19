from django.urls import re_path

from . import views

urlpatterns = [
    
    re_path( r'^states$',
             views.StatesView.as_view(),
             name = 'hass_api_states' ),

    re_path( r'^states/(?P<entity_id>\w+)$',
             views.StatesView.as_view(),
             name = 'hass_api_states_set' ),
]

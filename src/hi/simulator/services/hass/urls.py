from django.urls import path
from django.urls import include

from . import views

urlpatterns = [

    path( '',
          views.HomeView.as_view(),
          name = 'hass_home' ),

    path( 'api/', include('hi.simulator.services.hass.api.urls' )),
]

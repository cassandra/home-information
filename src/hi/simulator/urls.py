from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path( 'admin/', admin.site.urls ),

    path( '',
          RedirectView.as_view( pattern_name = 'simulator_services', permanent = False ),
          name = 'simulator_home' ),

    path( 'services/', include( 'hi.simulator.services.urls' )),
    path( 'weather/', include( 'hi.simulator.weather_sources.urls' )),
    path( 'scenes/', include( 'hi.simulator.scenes.urls' )),
    path( 'settings/', include( 'hi.simulator.settings.urls' )),
    path( 'profile/', include( 'hi.simulator.profile.urls' )),
]

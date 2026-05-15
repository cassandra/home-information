from django.urls import path
from django.urls import include

from . import views

urlpatterns = [

    path( '',
          views.HomeView.as_view(),
          name = 'zoneminder_home' ),

    # Portal-level paths the HI integration requests for media:
    # event thumbnails go through index.php?view=image, and live /
    # event playback streams go through cgi-bin/nph-zms.
    path( 'index.php',
          views.IndexPhpView.as_view(),
          name = 'zoneminder_index_php' ),

    path( 'cgi-bin/nph-zms',
          views.NphZmsView.as_view(),
          name = 'zoneminder_nph_zms' ),

    path( 'api/', include('hi.simulator.services.zoneminder.api.urls' )),
]

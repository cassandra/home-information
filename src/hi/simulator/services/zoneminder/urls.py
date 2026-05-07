from django.urls import include, re_path

from . import views

urlpatterns = [

    re_path( r'^$',
             views.HomeView.as_view(),
             name = 'zoneminder_home' ),

    # Portal-level paths the HI integration requests for media:
    # event thumbnails go through index.php?view=image, and live /
    # event playback streams go through cgi-bin/nph-zms.
    re_path( r'^index\.php$',
             views.IndexPhpView.as_view(),
             name = 'zoneminder_index_php' ),

    re_path( r'^cgi-bin/nph-zms$',
             views.NphZmsView.as_view(),
             name = 'zoneminder_nph_zms' ),

    re_path( r'^api/', include('hi.simulator.services.zoneminder.api.urls' )),
]

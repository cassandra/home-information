from django.urls import include, re_path

from . import views

urlpatterns = [

    re_path( r'^$',
             views.HomeView.as_view(),
             name = 'zoneminder_home' ),

    re_path( r'^api/', include('hi.simulator.services.zoneminder.api.urls' )),
]

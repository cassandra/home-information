from django.urls import path
from django.urls import include

from . import views

urlpatterns = [

    path( '',
          views.HomeView.as_view(),
          name = 'homebox_home' ),

    path( 'item/<str:item_id>/',
          views.ItemView.as_view(),
          name = 'homebox_item' ),

    path( 'api/', include('hi.simulator.services.homebox.api.urls' )),
]

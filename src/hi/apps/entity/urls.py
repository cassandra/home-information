from django.urls import include, re_path

from . import async_views


urlpatterns = [

    re_path( r'^info/(?P<entity_id>\d+)$', 
             async_views.EntityInfoView.as_view(), 
             name='entity_info' ),

    re_path( r'^details/(?P<entity_id>\d+)$', 
             async_views.EntityDetailsView.as_view(), 
             name='entity_details' ),

    re_path( r'^edit/', include('hi.apps.entity.edit.urls' )),

]

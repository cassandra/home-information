from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^details/(?P<entity_id>\d+)$', 
             views.EntityDetailsView.as_view(), 
             name='entity_details' ),

    re_path( r'^edit/', include('hi.apps.entity.edit.urls' )),

]

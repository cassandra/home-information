from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^entity/details/(?P<entity_id>\d+)$', 
             views.EntityDetailsView.as_view(), 
             name='entity_edit_entity_details' ),
    
]

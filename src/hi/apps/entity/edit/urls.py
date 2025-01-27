from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^entity/add$', 
             views.EntityAddView.as_view(), 
             name='entity_edit_entity_add' ),

    re_path( r'^entity/delete/(?P<entity_id>\d+)$', 
             views.EntityDeleteView.as_view(), 
             name='entity_edit_entity_delete' ),

    re_path( r'^entity/position/(?P<entity_id>\d+)$', 
             views.EntityPositionEditView.as_view(), 
             name='entity_position_edit' ),

    re_path( r'^entity/principal/manage/(?P<entity_id>\d+)$', 
             views.ManagePairingsView.as_view(), 
             name='entity_edit_manage_pairings' ),
]

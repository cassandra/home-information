from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^add$', 
             views.EntityAddView.as_view(), 
             name='entity_edit_entity_add' ),

    re_path( r'^delete/(?P<entity_id>\d+)$', 
             views.EntityDeleteView.as_view(), 
             name='entity_edit_entity_delete' ),

    re_path( r'^position/(?P<entity_id>\d+)$', 
             views.EntityPositionEditView.as_view(), 
             name='entity_position_edit' ),

    re_path( r'^principal/manage/(?P<entity_id>\d+)$', 
             views.ManagePairingsView.as_view(), 
             name='entity_edit_manage_pairings' ),

    re_path( r'^edit-mode/(?P<entity_id>\d+)$', 
             views.EntityEditModeView.as_view(), 
             name='entity_edit_mode' ),

    re_path( r'^properties/edit/(?P<entity_id>\d+)$', 
             views.EntityPropertiesEditView.as_view(), 
             name='entity_properties_edit'),
]

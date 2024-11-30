from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^info/(?P<entity_id>\d+)$', 
             views.EntityInfoView.as_view(), 
             name='entity_info' ),

    re_path( r'^details/(?P<entity_id>\d+)$', 
             views.EntityDetailsView.as_view(), 
             name='entity_details' ),

    re_path( r'^entity/edit/(?P<entity_id>\d+)$', 
             views.EntityEditView.as_view(), 
             name='entity_edit'),

    re_path( r'^entity/attribute/upload/(?P<entity_id>\d+)$', 
             views.EntityAttributeUploadView.as_view(), 
             name='entity_attribute_upload'),
    
    re_path( r'^edit/', include('hi.apps.entity.edit.urls' )),

]

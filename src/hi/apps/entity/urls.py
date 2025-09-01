from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^entity/edit/(?P<entity_id>\d+)$', 
             views.EntityEditView.as_view(), 
             name='entity_edit'),


    re_path( r'^status/(?P<entity_id>\d+)$', 
             views.EntityStatusView.as_view(), 
             name='entity_status' ),

    re_path( r'^state/history/(?P<entity_id>\d+)$', 
             views.EntityStateHistoryView.as_view(), 
             name='entity_state_history' ),


    re_path( r'^attribute/upload/(?P<entity_id>\d+)$', 
             views.EntityAttributeUploadView.as_view(), 
             name='entity_attribute_upload'),
    

    re_path( r'^entity/(?P<entity_id>\d+)/attribute/(?P<attribute_id>\d+)/history/inline/$', 
             views.EntityAttributeHistoryInlineView.as_view(), 
             name='entity_attribute_history_inline'),
    
    re_path( 
        r'^entity/(?P<entity_id>\d+)/attribute/(?P<attribute_id>\d+)/restore/inline/(?P<history_id>\d+)/$', 
        views.EntityAttributeRestoreInlineView.as_view(), 
        name='entity_attribute_restore_inline'
    ),

    re_path( r'^edit/', include('hi.apps.entity.edit.urls' )),

]

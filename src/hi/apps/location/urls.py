from django.urls import path
from django.urls import include, re_path

from . import views


urlpatterns = [

    path( 'switch/<int:location_id>', 
          views.LocationSwitchView.as_view(), 
          name='location_switch'),

    path( 'edit/<int:location_id>', 
          views.LocationEditView.as_view(), 
          name='location_edit_location_edit'),
        
    path( 'view/<int:location_view_id>', 
          views.LocationViewView.as_view(), 
          name='location_view'),

    path( 'view', 
          views.LocationViewDefaultView.as_view(), 
          name='location_view_default'),

    re_path( r'^item/status/(?P<html_id>[\w\-]+)$', 
             views.LocationItemStatusView.as_view(), 
             name='location_item_status' ),

    path( 'attribute/upload/<int:location_id>', 
          views.LocationAttributeUploadView.as_view(), 
          name='location_attribute_upload'),
    
    path( 'attribute/history/<int:location_id>/<int:attribute_id>', 
          views.LocationAttributeHistoryInlineView.as_view(), 
          name='location_attribute_history_inline'),
    
    path( 'attribute/restore/<int:location_id>/<int:attribute_id>/<int:history_id>', 
          views.LocationAttributeRestoreInlineView.as_view(), 
          name='location_attribute_restore_inline'),

    path( 'attribute/restore-deleted/<int:location_id>/<int:attribute_id>/',
          views.LocationAttributeRestoreDeletedInlineView.as_view(),
          name='location_attribute_restore_deleted_inline'),
    
    path( 'edit/', include('hi.apps.location.edit.urls' )),

]

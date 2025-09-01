from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^switch/(?P<location_id>\d+)$', 
             views.LocationSwitchView.as_view(), 
             name='location_switch'),

    re_path( r'^edit/(?P<location_id>\d+)$', 
             views.LocationEditView.as_view(), 
             name='location_edit_location_edit'),
        
    re_path( r'^view/(?P<location_view_id>\d+)$', 
             views.LocationViewView.as_view(), 
             name='location_view'),

    re_path( r'^view$', 
             views.LocationViewDefaultView.as_view(), 
             name='location_view_default'),

    re_path( r'^item/status/(?P<html_id>[\w\-]+)$', 
             views.LocationItemStatusView.as_view(), 
             name='location_item_status' ),

    re_path( r'^attribute/upload/(?P<location_id>\d+)$', 
             views.LocationAttributeUploadView.as_view(), 
             name='location_attribute_upload'),
    
    re_path( r'^attribute/history/(?P<location_id>\d+)/(?P<attribute_id>\d+)$', 
             views.LocationAttributeHistoryInlineView.as_view(), 
             name='location_attribute_history_inline'),
    
    re_path( r'^attribute/restore/(?P<location_id>\d+)/(?P<attribute_id>\d+)/(?P<history_id>\d+)$', 
             views.LocationAttributeRestoreInlineView.as_view(), 
             name='location_attribute_restore_inline'),
    
    re_path( r'^edit/', include('hi.apps.location.edit.urls' )),

]

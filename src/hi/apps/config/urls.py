from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^settings$', 
             views.ConfigSettingsView.as_view(), 
             name='config_settings' ),

    re_path( r'^internal$', 
             views.ConfigInternalView.as_view(), 
             name='config_internal' ),
    
    re_path( r'^attribute/history/(?P<attribute_id>\d+)$', 
             views.ConfigAttributeHistoryView.as_view(), 
             name='config_attribute_history'),
    
    re_path( r'^attribute/restore/(?P<attribute_id>\d+)$', 
             views.ConfigAttributeRestoreView.as_view(), 
             name='config_attribute_restore'),

]

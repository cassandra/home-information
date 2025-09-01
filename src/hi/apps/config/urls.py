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
    
    # Inline history and restore patterns expected by AttributeEditContext
    re_path( r'^attribute/history/(?P<subsystem_id>\d+)/(?P<attribute_id>\d+)/$', 
             views.SubsystemAttributeHistoryInlineView.as_view(), 
             name='subsystem_attribute_history_inline'),
    
    re_path( r'^attribute/restore/(?P<subsystem_id>\d+)/(?P<attribute_id>\d+)/(?P<history_id>\d+)/$', 
             views.SubsystemAttributeRestoreInlineView.as_view(),
             name='subsystem_attribute_restore_inline'),

]

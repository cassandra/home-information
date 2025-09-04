from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$', 
             views.ConfigHomeView.as_view(), 
             name='config_home' ),

    re_path( r'^settings(?:/(?P<subsystem_id>\d+))?$', 
             views.ConfigSettingsView.as_view(), 
             name='config_settings' ),

    re_path( r'^internal$', 
             views.ConfigInternalView.as_view(), 
             name='config_internal' ),
    
    # Inline history and restore patterns expected by AttributeItemEditContext
    re_path( r'^attribute/history/(?P<subsystem_id>\d+)/(?P<attribute_id>\d+)/$', 
             views.SubsystemAttributeHistoryInlineView.as_view(), 
             name='subsystem_attribute_history_inline'),
    
    re_path( r'^attribute/restore/(?P<subsystem_id>\d+)/(?P<attribute_id>\d+)/(?P<history_id>\d+)/$', 
             views.SubsystemAttributeRestoreInlineView.as_view(),
             name='subsystem_attribute_restore_inline'),

]

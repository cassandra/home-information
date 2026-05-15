from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( '', 
          views.ConfigHomeView.as_view(), 
          name='config_home' ),

    re_path( r'^settings(?:/(?P<subsystem_id>\d+))?$', 
             views.ConfigSettingsView.as_view(), 
             name='config_settings' ),


    path( 'attribute/history/<int:subsystem_id>/<int:attribute_id>/', 
          views.SubsystemAttributeHistoryInlineView.as_view(), 
          name='subsystem_attribute_history_inline'),
    
    path( 'attribute/restore/<int:subsystem_id>/<int:attribute_id>/<int:history_id>/', 
          views.SubsystemAttributeRestoreInlineView.as_view(),
          name='subsystem_attribute_restore_inline'),

    path( 'attribute/restore/default/subsystem/confirm/<int:subsystem_id>/',
          views.SubsystemAttributeRestoreSubsystemConfirmModalView.as_view(),
          name='subsystem_attribute_restore_subsystem_confirm_modal' ),

    path( 'attribute/restore/default/subsystem/<int:subsystem_id>/', 
          views.SubsystemAttributeRestoreSubsystemInlineView.as_view(),
          name='subsystem_attribute_restore_subsystem_inline' ),
    
    path( 'attribute/restore/default/all/confirm/<int:subsystem_id>/',
          views.SubsystemAttributeRestoreAllConfirmModalView.as_view(),
          name='subsystem_attribute_restore_all_confirm_modal' ),

    path( 'attribute/restore/default/all/<int:subsystem_id>/',
          views.SubsystemAttributeRestoreAllInlineView.as_view(),
          name='subsystem_attribute_restore_all_inline' ),
]

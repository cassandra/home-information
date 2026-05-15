from django.urls import path
from django.urls import include

from . import views


urlpatterns = [

    path( 'entity/edit/<int:entity_id>', 
          views.EntityEditView.as_view(), 
          name='entity_edit'),

    path( 'status/<int:entity_id>', 
          views.EntityStatusView.as_view(), 
          name='entity_status' ),

    path( 'history/<int:entity_id>',
          views.EntityHistoryView.as_view(),
          name='entity_history' ),

    path( 'state/<int:entity_state_id>/history',
          views.EntityStateHistoryView.as_view(),
          name='entity_state_history' ),

    path( 'attribute/upload/<int:entity_id>', 
          views.EntityAttributeUploadView.as_view(), 
          name='entity_attribute_upload' ),

    path( 'attribute/history/<int:entity_id>/<int:attribute_id>/', 
          views.EntityAttributeHistoryInlineView.as_view(), 
          name='entity_attribute_history_inline' ),
    
    path( 'attribute/restore/<int:entity_id>/<int:attribute_id>/<int:history_id>/', 
          views.EntityAttributeRestoreInlineView.as_view(), 
          name='entity_attribute_restore_inline' ),

    path( 'attribute/restore-deleted/<int:entity_id>/<int:attribute_id>/',
          views.EntityAttributeRestoreDeletedInlineView.as_view(),
          name='entity_attribute_restore_deleted_inline' ),

    path( 'edit/', include('hi.apps.entity.edit.urls' )),

]

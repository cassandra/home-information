from django.urls import path

from . import views


urlpatterns = [

    path( 'add', 
          views.EntityAddView.as_view(), 
          name='entity_edit_entity_add' ),

    path( 'delete/<int:entity_id>', 
          views.EntityDeleteView.as_view(), 
          name='entity_edit_entity_delete' ),

    path( 'position/<int:entity_id>', 
          views.EntityPositionEditView.as_view(), 
          name='entity_position_edit' ),

    path( 'principal/manage/<int:entity_id>', 
          views.ManagePairingsView.as_view(), 
          name='entity_edit_manage_pairings' ),

    path( 'edit-mode/<int:entity_id>', 
          views.EntityEditModeView.as_view(), 
          name='entity_edit_mode' ),

    path( 'properties/edit/<int:entity_id>',
          views.EntityPropertiesEditView.as_view(),
          name='entity_properties_edit'),

    path( 'archive/<int:entity_id>',
          views.EntityArchiveView.as_view(),
          name='entity_edit_entity_archive' ),

    path( 'archive-list/',
          views.EntityArchiveListView.as_view(),
          name='entity_edit_archive_list' ),

    path( 'archive-detail/<int:archived_entity_id>',
          views.EntityArchiveDetailView.as_view(),
          name='entity_edit_archive_detail' ),
]

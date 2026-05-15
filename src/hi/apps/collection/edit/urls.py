from django.urls import path

from . import views


urlpatterns = [

    path( 'add', 
          views.CollectionAddView.as_view(), 
          name='collection_add' ),

    path( 'edit-mode/<int:collection_id>', 
          views.CollectionEditModeView.as_view(), 
          name='collection_edit_mode'),

    path( 'properties/<int:collection_id>', 
          views.CollectionPropertiesEditView.as_view(), 
          name='collection_properties_edit'),

    path( 'delete/<int:collection_id>', 
          views.CollectionDeleteView.as_view(), 
          name='collection_edit_collection_delete' ),

    path( 'position/<int:collection_id>', 
          views.CollectionPositionEditView.as_view(), 
          name='collection_position_edit' ),

    path( 'manage-item', 
          views.CollectionManageItemsView.as_view(), 
          name='collection_edit_collection_manage_items' ),

    path( 'entity/toggle/<int:collection_id>/<int:entity_id>', 
          views.CollectionEntityToggleView.as_view(), 
          name='collection_edit_collection_entity_toggle' ),
    
]

from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^add$', 
             views.CollectionAddView.as_view(), 
             name='collection_add' ),

    re_path( r'^edit-mode/(?P<collection_id>\d+)$', 
             views.CollectionEditModeView.as_view(), 
             name='collection_edit_mode'),

    re_path( r'^properties/(?P<collection_id>\d+)$', 
             views.CollectionPropertiesEditView.as_view(), 
             name='collection_properties_edit'),

    re_path( r'^delete/(?P<collection_id>\d+)$', 
             views.CollectionDeleteView.as_view(), 
             name='collection_edit_collection_delete' ),

    re_path( r'^position/(?P<collection_id>\d+)$', 
             views.CollectionPositionEditView.as_view(), 
             name='collection_position_edit' ),

    re_path( r'^manage-item$', 
             views.CollectionManageItemsView.as_view(), 
             name='collection_edit_collection_manage_items' ),

    re_path( r'^entity/toggle/(?P<collection_id>\d+)/(?P<entity_id>\d+)$', 
             views.CollectionEntityToggleView.as_view(), 
             name='collection_edit_collection_entity_toggle' ),
    
]

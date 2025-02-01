from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^collection/add$', 
             views.CollectionAddView.as_view(), 
             name='collection_add' ),

    re_path( r'^collection/edit/(?P<collection_id>\d+)$', 
             views.CollectionEditView.as_view(), 
             name='collection_edit'),

    re_path( r'^collection/delete/(?P<collection_id>\d+)$', 
             views.CollectionDeleteView.as_view(), 
             name='collection_edit_collection_delete' ),

    re_path( r'^collection/position/(?P<collection_id>\d+)$', 
             views.CollectionPositionEditView.as_view(), 
             name='collection_position_edit' ),

    re_path( r'^collection/manage-item$', 
             views.CollectionManageItemsView.as_view(), 
             name='collection_edit_collection_manage_items' ),

    re_path( r'^collection/entity/toggle/(?P<collection_id>\d+)/(?P<entity_id>\d+)$', 
             views.CollectionEntityToggleView.as_view(), 
             name='collection_edit_collection_entity_toggle' ),
    
]

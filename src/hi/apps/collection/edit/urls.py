from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^collection/add$', 
             views.CollectionAddView.as_view(), 
             name='collection_edit_collection_add' ),

    re_path( r'^collection/delete/(?P<collection_id>\d+)$', 
             views.CollectionDeleteView.as_view(), 
             name='collection_edit_collection_delete' ),

    re_path( r'^collection/details/(?P<collection_id>\d+)$', 
             views.CollectionDetailsView.as_view(), 
             name='collection_edit_collection_details' ),

    re_path( r'^collection/add-remove-item$', 
             views.CollectionAddRemoveItemView.as_view(), 
             name='collection_edit_collection_add_remove_item' ),

    re_path( r'^collection/entity/toggle/(?P<collection_id>\d+)/(?P<entity_id>\d+)$', 
             views.CollectionEntityToggleView.as_view(), 
             name='collection_edit_collection_entity_toggle' ),
    
]

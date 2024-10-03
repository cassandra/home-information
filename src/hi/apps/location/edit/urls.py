from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^location-view/add$', 
             views.LocationViewAddView.as_view(), 
             name='location_edit_location_view_add' ),

    re_path( r'^location-view/delete$', 
             views.LocationViewDeleteView.as_view(), 
             name='location_edit_location_view_delete' ),

    re_path( r'^location-view/add-remove-item$', 
             views.LocationViewAddRemoveItemView.as_view(), 
             name='location_edit_location_view_add_remove_item' ),

    re_path( r'^location-view/entity/toggle/(?P<location_view_id>[\w\-]+)/(?P<entity_id>[\w\-]+)$', 
             views.LocationViewEntityToggleView.as_view(), 
             name='location_edit_location_view_entity_toggle' ),

    re_path( r'^location-view/collection/toggle/(?P<location_view_id>[\w\-]+)/(?P<collection_id>[\w\-]+)$', 
             views.LocationViewEntityToggleCollectionView.as_view(), 
             name='location_edit_location_view_collection_toggle' ),
]

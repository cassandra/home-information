from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^location/add$', 
             views.LocationAddView.as_view(), 
             name='location_edit_location_add'),

    re_path( r'^location/edit/(?P<location_id>\d+)$', 
             views.LocationEditView.as_view(), 
             name='location_edit_location_edit'),

    re_path( r'^location/delete/(?P<location_id>\d+)$', 
             views.LocationDeleteView.as_view(), 
             name='location_edit_location_delete' ),

    re_path( r'^location-view/add$', 
             views.LocationViewAddView.as_view(), 
             name='location_edit_location_view_add' ),

    re_path( r'^location-view/edit/(?P<location_view_id>\d+)$', 
             views.LocationViewEditView.as_view(), 
             name='location_edit_location_view_edit' ),

    re_path( r'^location-view/geometry/(?P<location_view_id>\d+)$', 
             views.LocationViewGeometryView.as_view(), 
             name='location_edit_location_view_geometry' ),

    re_path( r'^location-view/delete/(?P<location_view_id>\d+)$', 
             views.LocationViewDeleteView.as_view(), 
             name='location_edit_location_view_delete' ),

    re_path( r'^location-view/add-remove-item$', 
             views.LocationViewAddRemoveItemView.as_view(), 
             name='location_edit_location_view_add_remove_item' ),

    re_path( r'^location-view/entity/toggle/(?P<location_view_id>\d+)/(?P<entity_id>\d+)$', 
             views.LocationViewEntityToggleView.as_view(), 
             name='location_edit_location_view_entity_toggle' ),

    re_path( r'^location-view/collection/toggle/(?P<location_view_id>\d+)/(?P<collection_id>\d+)$', 
             views.LocationViewCollectionToggleView.as_view(), 
             name='location_edit_location_view_collection_toggle' ),

    re_path( r'^location-item/position/(?P<html_id>[\w\-]+)$', 
             views.LocationItemPositionView.as_view(), 
             name='location_edit_location_item_position' ),

    re_path( r'^location-item/path/(?P<html_id>[\w\-]+)$', 
             views.LocationItemPathView.as_view(), 
             name='location_edit_location_item_path' ),
    
]

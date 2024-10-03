from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^start$', 
             views.EditStartView.as_view(),
             name='edit_start' ),

    re_path( r'^end$', 
             views.EditEndView.as_view(), 
             name='edit_end' ),

    re_path( r'^details/(?P<html_id>[\w\-]*)$', 
             views.EditDetailsView.as_view(), 
             name='edit_details' ),

    re_path( r'^svg/position/(?P<html_id>[\w\-]+)$', 
             views.EditSvgPositionView.as_view(), 
             name='edit_svg_position' ),

    re_path( r'^add-remove$', 
             views.AddRemoveView.as_view(), 
             name='edit_add_remove' ),

    re_path( r'^location/entity/toggle/(?P<location_view_id>[\w\-]+)/(?P<entity_id>[\w\-]+)$', 
             views.EntityToggleLocationView.as_view(), 
             name='edit_entity_toggle_location' ),

    re_path( r'^location/collection/toggle/(?P<location_view_id>[\w\-]+)/(?P<collection_id>[\w\-]+)$', 
             views.CollectionToggleLocationView.as_view(), 
             name='edit_collection_toggle_location' ),

    re_path( r'^collection/entity/toggle/(?P<collection_id>[\w\-]+)/(?P<entity_id>[\w\-]+)$', 
             views.EntityToggleCollectionView.as_view(), 
             name='edit_entity_toggle_collection' ),

]

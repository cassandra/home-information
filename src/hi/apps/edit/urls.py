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
             views.EditAddRemoveView.as_view(), 
             name='edit_add_remove' ),

    re_path( r'^view/entity/toggle/(?P<location_view_id>[\w\-]+)/(?P<entity_id>[\w\-]+)$', 
             views.EditViewEntityToggleView.as_view(), 
             name='edit_view_entity_toggle' ),

    re_path( r'^view/collection/toggle/(?P<location_view_id>[\w\-]+)/(?P<collection_id>[\w\-]+)$', 
             views.EditViewCollectionToggleView.as_view(), 
             name='edit_view_collection_toggle' ),

]

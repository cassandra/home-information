from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^start$', 
             views.EditStartView.as_view(),
             name='edit_start' ),

    re_path( r'^end$', 
             views.EditEndView.as_view(), 
             name='edit_end' ),

    re_path( r'^delete$', 
             views.EditDeleteView.as_view(), 
             name='edit_delete' ),

    re_path( r'^svg/position/(?P<html_id>[\w\-]+)$', 
             views.EditLocationItemPositionView.as_view(), 
             name='edit_svg_position' ),

    re_path( r'^svg/path/(?P<html_id>[\w\-]+)$', 
             views.EditLocationItemPathView.as_view(), 
             name='edit_svg_path' ),

    re_path( r'^add-remove$', 
             views.AddRemoveView.as_view(), 
             name='edit_add_remove' ),

    re_path( r'^reorder-items$', 
             views.ReorderItemsView.as_view(), 
             name='edit_reorder_items' ),

]

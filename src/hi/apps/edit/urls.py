from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^start$', 
             views.EditStartView.as_view(),
             name='edit_start' ),

    re_path( r'^end$', 
             views.EditEndView.as_view(), 
             name='edit_end' ),

    re_path( r'^item/reorder$', 
             views.ReorderItemsView.as_view(), 
             name='edit_reorder_items' ),

    re_path( r'^item/details/close$', 
             views.ItemDetailsCloseView.as_view(), 
             name='edit_item_details_close' ),

]

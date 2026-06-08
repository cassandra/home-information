from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( 'start', 
          views.EditStartView.as_view(),
          name='edit_start' ),

    path( 'end', 
          views.EditEndView.as_view(), 
          name='edit_end' ),

    path( 'item/reorder', 
          views.ReorderItemsView.as_view(), 
          name='edit_reorder_items' ),

    path( 'item/details/close',
          views.ItemDetailsCloseView.as_view(),
          name='edit_item_details_close' ),

    path( 'entity/view-membership/toggle/<int:entity_id>',
          views.EntityViewMembershipToggleView.as_view(),
          name='edit_entity_view_membership_toggle' ),

    re_path( r'^entity/state/values/(?P<instance_name>\w+)/(?P<instance_id>\d+)$',
             views.EntityStateValueChoicesView.as_view(), 
             name='edit_entity_state_value_choices' ),
    
]

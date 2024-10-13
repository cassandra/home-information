
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^enable$', 
             views.HassEnableView.as_view(), 
             name='hass_enable' ),

    re_path( r'^disable$', 
             views.HassDisableView.as_view(), 
             name='hass_disable' ),

    re_path( r'^manage$', 
             views.HassManageView.as_view(), 
             name='hass_manage' ),

    re_path( r'^sync$', 
             views.HassSyncView.as_view(), 
             name='hass_sync' ),

]


from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^enable$', 
             views.ZmEnableView.as_view(), 
             name='zm_enable' ),

    re_path( r'^disable$', 
             views.ZmDisableView.as_view(), 
             name='zm_disable' ),

    re_path( r'^manage$', 
             views.ZmManageView.as_view(), 
             name='zm_manage' ),

    re_path( r'^sync$', 
             views.ZmSyncView.as_view(), 
             name='zm_sync' ),

]

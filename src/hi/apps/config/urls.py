from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$', 
             views.ConfigHomePaneView.as_view(), 
             name='config_home_pane' ),

    re_path( r'^tab$', 
             views.ConfigTabPaneView.as_view(), 
             name='config_tab_pane' ),

]

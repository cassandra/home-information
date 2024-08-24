
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^config/(?P<name>\w+)/(?P<action>\w+)$', 
             views.IntegrationConfigTabView.as_view(), 
             name='integration_config' ),

    re_path( r'^manage/(?P<name>\w+)$', 
             views.IntegrationManageView.as_view(), 
             name='integration_manage' ),
]


from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^$', 
             views.IntegrationHomeView.as_view(), 
             name='integrations_home' ),

    re_path( r'^select$', 
             views.IntegrationSelectView.as_view(), 
             name='integrations_select' ),

    re_path( r'^enable/(?P<integration_id>[\w\-]+)$', 
             views.IntegrationEnableView.as_view(), 
             name='integrations_enable' ),

    re_path( r'^disable/(?P<integration_id>[\w\-]+)$', 
             views.IntegrationDisableView.as_view(), 
             name='integrations_disable' ),

    re_path( r'^manage/(?P<integration_id>[\w\-]*)$', 
             views.IntegrationManageView.as_view(), 
             name='integrations_manage' ),

    re_path( r'^zm/', include('hi.integrations.zoneminder.urls' )),

    re_path( r'^hass/', include('hi.integrations.hass.urls' )),
]

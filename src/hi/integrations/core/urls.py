
from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^$', 
             views.IntegrationsHomeView.as_view(), 
             name='integrations_home' ),

    re_path( r'^enable/(?P<integration_id>[\w\-]+)$', 
             views.IntegrationsEnableView.as_view(), 
             name='integrations_enable' ),

    re_path( r'^disable/(?P<integration_id>[\w\-]+)$', 
             views.IntegrationsDisableView.as_view(), 
             name='integrations_disable' ),

    re_path( r'^manage$', 
             views.IntegrationsManageView.as_view(), 
             name='integrations_manage' ),

    re_path( r'^zm/', include('hi.integrations.zoneminder.urls' )),

    re_path( r'^hass/', include('hi.integrations.hass.urls' )),
]

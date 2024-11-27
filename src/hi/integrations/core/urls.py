
from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^$', 
             views.IntegrationsHomeView.as_view(), 
             name='integrations_home' ),

    re_path( r'^manage$', 
             views.IntegrationsManageView.as_view(), 
             name='integrations_manage' ),

    re_path( r'^action/(?P<integration_id>[\w\-]+)/(?P<action>[\w\-]+)$', 
             views.IntegrationActionView.as_view(), 
             name='integrations_action' ),

    re_path( r'^zm/', include('hi.integrations.zoneminder.urls' )),

    re_path( r'^hass/', include('hi.integrations.hass.urls' )),


    re_path( r'^sensor/response/details/(?P<sensor_history_id>\d+)$', 
             views.SensorResponseDetailsView.as_view(), 
             name='integration_sensor_response_details'),

    
]

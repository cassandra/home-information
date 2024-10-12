
from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^action/(?P<name>[\w\-]+)/(?P<action>[\w\-]+)$', 
             views.IntegrationActionView.as_view(), 
             name='integration_action' ),

    re_path( r'^zm/', include('hi.integrations.zoneminder.urls' )),

    
]

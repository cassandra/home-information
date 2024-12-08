from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^acknowledge/(?P<alert_id>.+)$', 
             views.AlertAcknowledgeView.as_view(), 
             name='alert_acknowledge'),

    re_path( r'^details/(?P<alert_id>.+)$', 
             views.AlertDetailsView.as_view(), 
             name='alert_details'),
]

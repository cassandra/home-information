from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^state/action/(?P<action>.+)$', 
             views.SecurityStateActionView.as_view(), 
             name='security_state_action'),
]

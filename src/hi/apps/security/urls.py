from django.urls import path

from . import views


urlpatterns = [

    path( 'state/action/<path:action>', 
          views.SecurityStateActionView.as_view(), 
          name='security_state_action'),
]

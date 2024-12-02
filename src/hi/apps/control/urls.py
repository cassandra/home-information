from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^controller/(?P<controller_id>\d+)$', 
             views.ControllerView.as_view(), 
             name='control_controller'),
]

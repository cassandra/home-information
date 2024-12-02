from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^controller/(?P<controller_id>\d+)/discrete$', 
             views.ControllerDiscreteView.as_view(), 
             name='control_controller_discrete'),

    re_path( r'^controller/(?P<controller_id>\d+)/on-off$', 
             views.ControllerOnOffView.as_view(), 
             name='control_controller_on_off'),
]

from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^controller/(?P<controller_id>\d+)$', 
             views.ControllerView.as_view(), 
             name='control_controller'),

    re_path( r'^controller/history/(?P<controller_id>\d+)$', 
             views.ControllerHistoryView.as_view(), 
             name='control_controller_history'),
]

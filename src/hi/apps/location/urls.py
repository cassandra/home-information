from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^view/(?P<id>\d+)$', 
             views.LocationViewView.as_view(), 
             name='location_view'),

    re_path( r'^view$', 
             views.LocationViewDefaultView.as_view(), 
             name='location_view_default'),
    
]

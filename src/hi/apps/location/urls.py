from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^switch/(?P<location_id>\d+)$', 
             views.LocationSwitchView.as_view(), 
             name='location_switch'),

    re_path( r'^view/(?P<id>\d+)$', 
             views.LocationViewView.as_view(), 
             name='location_view'),

    re_path( r'^view$', 
             views.LocationViewDefaultView.as_view(), 
             name='location_view_default'),

    re_path( r'^edit/', include('hi.apps.location.edit.urls' )),

]

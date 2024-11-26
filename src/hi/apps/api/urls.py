from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^status$', 
             views.StatusView.as_view(), 
             name='api_status'),

]

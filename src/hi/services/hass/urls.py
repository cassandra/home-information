
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^sync$', 
             views.HassSyncView.as_view(), 
             name='hass_sync' ),

]

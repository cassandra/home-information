from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^permission-guidance$', 
             views.AudioPermissionGuidanceView.as_view(),
             name='audio_permission_guidance' ),
]

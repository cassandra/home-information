from django.urls import path

from . import views


urlpatterns = [

    path( 'permission-guidance', 
          views.AudioPermissionGuidanceView.as_view(),
          name='audio_permission_guidance' ),
]

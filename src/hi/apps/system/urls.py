from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( 'info', 
          views.SystemInfoView.as_view(), 
          name = 'system_info' ),

    re_path( r'^health/(?P<provider_id>[\w\.\-]+)$',
             views.SystemHealthStatusView.as_view(),
             name = 'system_health_status' ),

    re_path( r'^api-health/(?P<provider_id>[\w\.\-]+)$',
             views.SystemApiHealthStatusView.as_view(),
             name = 'system_api_health_status' ),

    path( 'background-tasks/details',
          views.BackgroundTaskDetailsView.as_view(),
          name = 'background_task_details' ),
]

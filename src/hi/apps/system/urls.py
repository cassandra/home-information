from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^info$', 
             views.SystemInfoView.as_view(), 
             name = 'system_info' ),

    re_path( r'^health/<str:provider_id>$',
             views.SystemHealthStatusView.as_view(),
             name = 'system_health_status' ),

    re_path( r'^background-tasks/details$',
             views.BackgroundTaskDetailsView.as_view(),
             name = 'background_task_details' ),
]

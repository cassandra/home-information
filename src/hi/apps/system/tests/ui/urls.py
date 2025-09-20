from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$',
            views.SystemTestUiHomeView.as_view(),
            name='system_test_ui'),

    re_path(r'^health/(?P<status_type>[\w-]+)/(?P<api_flag>[\w-]+)/$',
            views.SystemTestUiHealthStatusView.as_view(),
            name='system_test_ui_health_status'),
]

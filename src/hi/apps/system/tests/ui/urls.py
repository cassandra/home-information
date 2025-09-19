from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$',
            views.SystemTestUiHomeView.as_view(),
            name='system_test_ui'),

    re_path(r'^health/(?P<monitor_type>\w+)$',
            views.SystemTestUiHealthStatusView.as_view(),
            name='system_test_ui_health_status'),
]

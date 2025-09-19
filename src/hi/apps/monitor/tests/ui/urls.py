from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$',
            views.TestUiMonitorHomeView.as_view(),
            name='monitor_tests_ui'),

    re_path(r'^health/(?P<monitor_type>\w+)/$',
            views.TestUiMonitorHealthStatusView.as_view(),
            name='test_monitor_health_status'),
]

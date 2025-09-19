from django.urls import path

from . import views

app_name = 'monitor'

urlpatterns = [
    path('health/<str:monitor_id>/', views.MonitorHealthStatusView.as_view(), name='health_status'),
]

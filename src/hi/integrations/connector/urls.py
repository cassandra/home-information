from django.urls import path, re_path

from . import views


urlpatterns = [
    path( '',
          views.IntegrationHomeView.as_view(),
          name='integrations_connect_home' ),
    path( 'select',
          views.IntegrationSelectView.as_view(),
          name='integrations_connect_select' ),
    re_path( r'^enable/(?P<integration_id>[\w\-]+)$',
             views.ConnectorConfigureView.as_view(),
             name='integrations_connect_configure' ),
    re_path( r'^disable/(?P<integration_id>[\w\-]+)$',
             views.IntegrationDisableView.as_view(),
             name='integrations_connect_disable' ),
    re_path( r'^pause/(?P<integration_id>[\w\-]+)$',
             views.IntegrationPauseView.as_view(),
             name='integrations_connect_pause' ),
    re_path( r'^resume/(?P<integration_id>[\w\-]+)$',
             views.IntegrationResumeView.as_view(),
             name='integrations_connect_resume' ),
    re_path( r'^health/(?P<integration_id>[\w\-]+)$',
             views.IntegrationHealthStatusView.as_view(),
             name='integrations_connect_health_status' ),
    re_path( r'^pre-sync/(?P<integration_id>[\w\-]+)$',
             views.IntegrationPreSyncView.as_view(),
             name='integrations_connect_pre_sync' ),
    re_path( r'^sync/(?P<integration_id>[\w\-]+)$',
             views.IntegrationSyncView.as_view(),
             name='integrations_connect_sync' ),
    re_path( r'^manage/(?P<integration_id>[\w\-]*)$',
             views.ConnectorManageView.as_view(),
             name='integrations_connect_manage' ),
]

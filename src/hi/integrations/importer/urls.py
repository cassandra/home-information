from django.urls import path, re_path

from . import views


urlpatterns = [
    path( '',
          views.DataImportPageView.as_view(),
          name='integrations_import_home' ),
    path( 'info',
          views.DataImportInfoView.as_view(),
          name='integrations_import_info' ),
    re_path( r'^configure/(?P<integration_id>[\w\-]+)$',
             views.ImporterConfigureView.as_view(),
             name='integrations_import_configure' ),
    re_path( r'^run/(?P<integration_id>[\w\-]+)$',
             views.ImporterRunView.as_view(),
             name='integrations_import_run' ),
    re_path( r'^discard/(?P<integration_id>[\w\-]+)$',
             views.ImporterDiscardView.as_view(),
             name='integrations_import_discard' ),
]

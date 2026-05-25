from django.apps import apps
from django.urls import path
from django.urls import re_path, include

from hi.apps.common.module_utils import import_module_safe

from .connector import views
from .importer import views as importer_views


urlpatterns = [
    path( '',
          views.IntegrationHomeView.as_view(),
          name='integrations_connect_home' ),

    path( 'import/',
          importer_views.DataImportPageView.as_view(),
          name='integrations_import_home' ),

    path( 'import/info',
          importer_views.DataImportInfoView.as_view(),
          name='integrations_import_info' ),

    re_path( r'^import/configure/(?P<integration_id>[\w\-]+)$',
             importer_views.ImporterConfigureView.as_view(),
             name='integrations_import_configure' ),

    re_path( r'^import/run/(?P<integration_id>[\w\-]+)$',
             importer_views.ImporterRunView.as_view(),
             name='integrations_import_run' ),

    re_path( r'^import/discard/(?P<integration_id>[\w\-]+)$',
             importer_views.ImporterDiscardView.as_view(),
             name='integrations_import_discard' ),

    path( 'select', 
          views.IntegrationSelectView.as_view(), 
          name='integrations_select' ),

    re_path( r'^enable/(?P<integration_id>[\w\-]+)$',
             views.ConnectorConfigureView.as_view(),
             name='integrations_connect_configure' ),

    re_path( r'^disable/(?P<integration_id>[\w\-]+)$',
             views.IntegrationDisableView.as_view(),
             name='integrations_disable' ),

    re_path( r'^pause/(?P<integration_id>[\w\-]+)$',
             views.IntegrationPauseView.as_view(),
             name='integrations_pause' ),

    re_path( r'^resume/(?P<integration_id>[\w\-]+)$',
             views.IntegrationResumeView.as_view(),
             name='integrations_resume' ),

    re_path( r'^health/(?P<integration_id>[\w\-]+)$',
             views.IntegrationHealthStatusView.as_view(),
             name='integrations_health_status' ),

    re_path( r'^pre-sync/(?P<integration_id>[\w\-]+)$',
             views.IntegrationPreSyncView.as_view(),
             name='integrations_pre_sync' ),

    re_path( r'^sync/(?P<integration_id>[\w\-]+)$',
             views.IntegrationSyncView.as_view(),
             name='integrations_sync' ),

    re_path( r'^placement/(?P<integration_id>[\w\-]+)$',
             views.IntegrationPlacementView.as_view(),
             name='integrations_placement' ),

    path( 'refine/<int:location_view_id>',
          views.IntegrationRefineView.as_view(),
          name='integrations_refine' ),

    re_path( r'^manage/(?P<integration_id>[\w\-]*)$',
             views.ConnectorManageView.as_view(),
             name='integrations_connect_manage' ),
    
    path( 'attribute/history/<int:integration_id>/<int:attribute_id>/', 
          views.IntegrationAttributeHistoryInlineView.as_view(), 
          name='integration_attribute_history_inline'),
    
    path( 'attribute/restore/<int:integration_id>/<int:attribute_id>/<int:history_id>/', 
          views.IntegrationAttributeRestoreInlineView.as_view(),
          name='integration_attribute_restore_inline'),
]


def discover_urls():
    """ Add urls (if any) from all integrations """
    
    discovered_url_modules = dict()
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith( 'hi.services' ):
            continue
        module_name = f'{app_config.name}.urls'
        short_name = app_config.name.split('.')[-1]
        try:
            urls_module = import_module_safe( module_name = module_name )
            if not urls_module:
                continue

            discovered_url_modules[short_name] = urls_module

        except Exception:
            pass
        continue

    return discovered_url_modules


for short_name, urls_module in discover_urls().items():
    urlpatterns.append(
        re_path(f"services/{short_name}/", include( urls_module ))
    )
    continue

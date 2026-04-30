from django.apps import apps
from django.urls import re_path, include

from hi.apps.common.module_utils import import_module_safe

from . import views


urlpatterns = [
    re_path( r'^$', 
             views.IntegrationHomeView.as_view(), 
             name='integrations_home' ),

    re_path( r'^select$', 
             views.IntegrationSelectView.as_view(), 
             name='integrations_select' ),

    re_path( r'^enable/(?P<integration_id>[\w\-]+)$', 
             views.IntegrationEnableView.as_view(), 
             name='integrations_enable' ),

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

    re_path( r'^dispatcher/(?P<integration_id>[\w\-]+)$',
             views.IntegrationDispatcherView.as_view(),
             name='integrations_dispatcher' ),

    re_path( r'^dispatcher/dismiss/(?P<integration_id>[\w\-]+)$',
             views.IntegrationDispatcherDismissView.as_view(),
             name='integrations_dispatcher_dismiss' ),

    re_path( r'^placements/apply/(?P<integration_id>[\w\-]+)$',
             views.IntegrationApplyPlacementsView.as_view(),
             name='integrations_apply_placements' ),

    re_path( r'^refine/(?P<location_view_id>\d+)$',
             views.IntegrationRefineView.as_view(),
             name='integrations_refine' ),

    re_path( r'^manage/(?P<integration_id>[\w\-]*)$', 
             views.IntegrationManageView.as_view(), 
             name='integrations_manage' ),
    
    re_path( r'^attribute/history/(?P<integration_id>\d+)/(?P<attribute_id>\d+)/$', 
             views.IntegrationAttributeHistoryInlineView.as_view(), 
             name='integration_attribute_history_inline'),
    
    re_path( r'^attribute/restore/(?P<integration_id>\d+)/(?P<attribute_id>\d+)/(?P<history_id>\d+)/$', 
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

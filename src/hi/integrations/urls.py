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

    re_path( r'^manage/(?P<integration_id>[\w\-]*)$', 
             views.IntegrationManageView.as_view(), 
             name='integrations_manage' ),
    
    re_path( r'^attribute/history/(?P<attribute_id>\d+)$', 
             views.IntegrationAttributeHistoryView.as_view(), 
             name='integration_attribute_history'),
    
    re_path( r'^attribute/restore/(?P<attribute_id>\d+)$', 
             views.IntegrationAttributeRestoreView.as_view(), 
             name='integration_attribute_restore'),
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

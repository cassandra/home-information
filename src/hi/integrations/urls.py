from django.apps import apps
from django.urls import path
from django.urls import re_path, include

from hi.apps.common.module_utils import import_module_safe

from . import views


urlpatterns = [
    path( 'connect/', include( 'hi.integrations.connector.urls' )),
    path( 'import/', include( 'hi.integrations.importer.urls' )),
    path( 'referencer/', include( 'hi.integrations.referencer.urls' )),

    re_path( r'^placement/(?P<integration_id>[\w\-]+)$',
             views.IntegrationPlacementView.as_view(),
             name='integrations_placement' ),
    path( 'refine/<int:location_view_id>',
          views.IntegrationRefineView.as_view(),
          name='integrations_refine' ),
    path( 'attribute/history/<int:integration_id>/<int:attribute_id>/',
          views.IntegrationAttributeHistoryInlineView.as_view(),
          name='integration_attribute_history_inline' ),
    path( 'attribute/restore/<int:integration_id>/<int:attribute_id>/<int:history_id>/',
          views.IntegrationAttributeRestoreInlineView.as_view(),
          name='integration_attribute_restore_inline' ),
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
        re_path( f"services/{short_name}/", include( urls_module ))
    )
    continue

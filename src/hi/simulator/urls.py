from django.apps import apps
from django.urls import include, re_path

from hi.apps.common.module_utils import import_module_safe

from . import views

urlpatterns = [
    re_path( r'^$', views.HomeView.as_view(), name = 'simulator_home' ),
    re_path( r'^add-device$', views.AddDeviceView.as_view(), name = 'simulator_add_device' ),
]


def discover_urls():
    """ Add urls (if any) from all simulated integration services """
    
    discovered_url_modules = dict()
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith( 'hi.simulator.services' ):
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

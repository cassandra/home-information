import logging

from django.apps import apps
from django.urls import include, path, re_path

from hi.apps.common.module_utils import import_module_safe

from . import views

logger = logging.getLogger(__name__)


urlpatterns = [
    path( '',
          views.WeatherIndexView.as_view(),
          name = 'simulator_weather' ),

    path( 'tab/<slug:short_name>/',
          views.WeatherSourceView.as_view(),
          name = 'simulator_weather_source' ),

    path( 'fault-mode/<slug:short_name>/set',
          views.WeatherFaultModeSetView.as_view(),
          name = 'simulator_weather_fault_mode_set' ),
]


def discover_weather_source_urls():
    """ Add urls (if any) from all simulated weather-source apps """
    discovered_url_modules = dict()
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith( 'hi.simulator.weather_sources.' ):
            continue
        module_name = f'{app_config.name}.urls'
        short_name = app_config.name.split('.')[-1]
        try:
            urls_module = import_module_safe( module_name = module_name )
            if not urls_module:
                continue
            discovered_url_modules[short_name] = urls_module
        except Exception:
            logger.exception( f'Problem importing URL module: {module_name}' )
            pass
        continue
    return discovered_url_modules


for short_name, urls_module in discover_weather_source_urls().items():
    urlpatterns.append(
        re_path( f"{short_name}/", include( urls_module ))
    )
    continue

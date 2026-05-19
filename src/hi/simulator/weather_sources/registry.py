"""Registry/discovery for simulator weather-source apps.

Each weather-source simulator is a Django app under
``hi.simulator.weather_sources.<short_name>``. Its ``AppConfig`` carries the
display metadata the simulator's weather page uses to build per-source
tabs:

* ``weather_source_short_name`` — slug used in URLs (e.g. ``nws``)
* ``weather_source_label`` — human label for the tab (e.g.
  ``National Weather Service``)
* ``weather_source_tab_template`` — template included into the
  weather page for that source's tab body

Parallels ``hi.simulator.services.*`` discovery used by the services
page.
"""
import logging
from dataclasses import dataclass
from typing import List

from django.apps import apps as django_apps


logger = logging.getLogger(__name__)


@dataclass
class WeatherSourceData:
    short_name : str
    label : str
    tab_template : str


def get_weather_source_data_list() -> List[ WeatherSourceData ]:
    results : List[ WeatherSourceData ] = []
    for app_config in django_apps.get_app_configs():
        if not app_config.name.startswith( 'hi.simulator.weather_sources.' ):
            continue
        try:
            results.append(
                WeatherSourceData(
                    short_name = app_config.weather_source_short_name,
                    label = app_config.weather_source_label,
                    tab_template = app_config.weather_source_tab_template,
                )
            )
        except AttributeError:
            logger.warning(
                f'Weather simulator app {app_config.name} is missing one of '
                'weather_source_short_name / weather_source_label / '
                'weather_source_tab_template attributes; skipping.'
            )
            continue
    results.sort( key = lambda item : item.label )
    return results

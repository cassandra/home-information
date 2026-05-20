"""Discovery of pluggable simulator modules.

A "module" here is any sub-app of ``hi.simulator.services.*`` or
``hi.simulator.weather_sources.*``. Each pluggable module declares
its operator-facing label via a ``simulator_module_label`` class
attribute on its AppConfig (single convention across services and
weather sources).
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from django.apps import apps as django_apps


logger = logging.getLogger(__name__)


_MODULE_NAME_PREFIXES = (
    'hi.simulator.services.',
    'hi.simulator.weather_sources.',
)


@dataclass(frozen=True)
class SimulatorModule:
    """Operator-visible identity of a single simulator module."""
    module_key : str    # AppConfig.name (full dotted path)
    label : str         # AppConfig.simulator_module_label


def discover_modules() -> List[ SimulatorModule ]:
    modules : List[ SimulatorModule ] = []
    for app_config in django_apps.get_app_configs():
        if not any( app_config.name.startswith( prefix )
                    for prefix in _MODULE_NAME_PREFIXES ):
            continue
        # Skip the parent sub-apps themselves (services, weather_sources);
        # only their sub-sub-apps are pluggable modules.
        if app_config.name.rstrip('.') in (
                'hi.simulator.services',
                'hi.simulator.weather_sources' ):
            continue
        label = getattr( app_config, 'simulator_module_label', None )
        if label is None:
            logger.warning(
                f'AppConfig {app_config.name} is missing '
                'simulator_module_label; module not registered.'
            )
            continue
        modules.append( SimulatorModule(
            module_key = app_config.name,
            label = label,
        ))
        continue
    modules.sort( key = lambda m : m.label )
    return modules


def find_module( module_key : str ) -> Optional[ SimulatorModule ]:
    for module in discover_modules():
        if module.module_key == module_key:
            return module
        continue
    return None

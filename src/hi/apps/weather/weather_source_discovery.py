import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class WeatherSourceDiscovery:
    """Centralized weather data source discovery utility."""
    
    @classmethod
    def discover_weather_data_source_instances(cls) -> List['WeatherDataSource']:
        """
        Discover all WeatherDataSource instances from the weather_sources directory.
        
        This is the single source of truth for weather source discovery,
        used by both the settings system and the monitoring system.
        """
        from .weather_data_source import WeatherDataSource
        
        sources_dir = os.path.join(Path(__file__).parent, 'weather_sources')
        logger.debug(f'Discovering weather sources in: {sources_dir}')

        discovered_sources = []
        
        try:
            for file in os.listdir(sources_dir):
                if not file.endswith(".py") or file == "__init__.py":
                    continue
                    
                module_name = f"hi.apps.weather.weather_sources.{file[:-3]}"
                
                try:
                    module = importlib.import_module(module_name)
                    
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, WeatherDataSource) and obj is not WeatherDataSource:
                            try:
                                source_instance = obj()
                                discovered_sources.append(source_instance)
                                logger.debug(f'Discovered weather source:'
                                             f' {source_instance.label} ({source_instance.id})')
                            except Exception as e:
                                logger.warning(f'Failed to instantiate weather source {name}: {e}')
                            continue
                except Exception as e:
                    logger.warning(f'Failed to import weather source module {module_name}: {e}')
                continue
        except Exception as e:
            logger.warning(f'Error accessing weather sources directory {sources_dir}: {e}')
            
        # Sort by priority (lower numbers = higher priority)
        discovered_sources.sort(key=lambda item: item.priority)
        return discovered_sources

from hi.apps.common.singleton import Singleton
from hi.apps.system.aggregate_health_provider import AggregateHealthProvider
from hi.apps.system.provider_info import ProviderInfo


class WeatherSourceManager( Singleton, AggregateHealthProvider ):

    def __init_singleton__(self):
        return
    
    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'hi.apps.weather.weather_sources',
            provider_name = 'Weather API Manager',
            description = '',            
        )

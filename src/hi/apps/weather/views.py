import logging
from hi.hi_async_view import HiModalView

from .weather_mixins import WeatherMixin
from .weather_sources.sunrise_sunset_org import SunriseSunsetOrg
from .weather_sources.usno import USNO

logger = logging.getLogger(__name__)


class CurrentConditionsDetailsView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/conditions_details.html'
    
    def get(self, request, *args, **kwargs):
        weather_overview_data = self.weather_manager().get_weather_overview_data()
        context = {
            'weather_conditions_data': weather_overview_data.current_conditions_data,
            'weather_stats': weather_overview_data.todays_weather_stats,
        }
        return self.modal_response( request, context )

    
class TodaysAstronomicalDetailsView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/astronomical_details.html'
    
    def get(self, request, *args, **kwargs):
        todays_astronomical_data = self.weather_manager().get_todays_astronomical_data()
        daily_astronomical_data = self.weather_manager().get_daily_astronomical_data()
        
        # Check if any astronomical data comes from sunrise-sunset-org source
        has_sunrise_sunset_data = bool(
            todays_astronomical_data
            and SunriseSunsetOrg.SOURCE_ID in {x.id for x in todays_astronomical_data.data_sources}
        )
        
        # Check if any astronomical data comes from USNO source
        has_usno_data = bool(
            todays_astronomical_data
            and USNO.SOURCE_ID in {x.id for x in todays_astronomical_data.data_sources}
        )
        
        context = {
            'todays_astronomical_data': todays_astronomical_data,
            'daily_astronomical_data': daily_astronomical_data,
            'has_sunrise_sunset_attribution': has_sunrise_sunset_data,
            'has_usno_attribution': has_usno_data,
        }
        return self.modal_response( request, context )

    
class ForecastView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/forecast.html'
    
    def get(self, request, *args, **kwargs):
        hourly_forecast = self.weather_manager().get_hourly_forecast()
        daily_forecast = self.weather_manager().get_daily_forecast()
        context = {
            'interval_hourly_forecast_list': hourly_forecast.data_list,
            'interval_daily_forecast_list': daily_forecast.data_list,
        }
        return self.modal_response( request, context )

    
class HistoryView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/history.html'
    
    def get(self, request, *args, **kwargs):
        daily_history = self.weather_manager().get_daily_history()
        logger.debug(f'History view: daily_history.data_list has {len(daily_history.data_list)} items')
        context = {
            'interval_daily_history_list': daily_history.data_list,
        }
        return self.modal_response( request, context )

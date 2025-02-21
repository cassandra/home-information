from hi.hi_async_view import HiModalView

from .weather_mixins import WeatherMixin


class CurrentConditionsDetailsView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/conditions_details.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'weather_conditions_data': self.weather_manager().get_current_conditions_data(),
        }
        return self.modal_response( request, context )

    
class TodaysAstronomicalDetailsView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/astronomical_details.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'daily_astronomical_data': self.weather_manager().get_todays_astronomical_data(),
        }
        return self.modal_response( request, context )

    
class ForecastView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/forecast.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'hourly_forecast_data_list': self.weather_manager().get_hourly_forecast_data_list,
            'daily_forecast_data_list': self.weather_manager().get_daily_forecast_data_list,
        }
        return self.modal_response( request, context )

    
class RadarView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/radar.html'
    
    def get(self, request, *args, **kwargs):
        context = {
        }
        return self.modal_response( request, context )

    
class HistoryView( HiModalView, WeatherMixin ):

    def get_template_name( self ) -> str:
        return 'weather/modals/history.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'daily_history_data_list': self.weather_manager().get_daily_history_data_list,
        }
        return self.modal_response( request, context )


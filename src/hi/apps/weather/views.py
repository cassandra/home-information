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


from hi.apps.security.security_mixins import SecurityMixin
from hi.apps.weather.weather_mixins import WeatherMixin

from .console_mixin import ConsoleMixin


class ConsoleSideHelper( ConsoleMixin, SecurityMixin, WeatherMixin ):
    
    def get_side_template_name_and_context( self, request, *args, **kwargs ):
        context = {
            'weather_overview_data': self.weather_manager().get_weather_overview_data(),
            'security_status_data': self.security_manager().get_security_status_data(),
            'video_stream_entity_list': self.console_manager().get_video_stream_entity_list(),
        }
        return ( 'console/panes/hi_grid_side.html', context )
 

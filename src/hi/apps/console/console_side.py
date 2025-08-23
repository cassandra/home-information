from hi.apps.security.security_mixins import SecurityMixin
from hi.apps.weather.weather_mixins import WeatherMixin

from .console_mixins import ConsoleMixin


class ConsoleSideHelper( ConsoleMixin, SecurityMixin, WeatherMixin ):
    
    def get_side_template_name_and_context( self, request, *args, **kwargs ):
        context = {
            'weather_overview_data': self.weather_manager().get_weather_overview_data(),
            'weather_alert_list': self.weather_manager().get_weather_alerts(),
            'security_status_data': self.security_manager().get_security_status_data(),
            'camera_control_display_list': self.console_manager().get_camera_control_display_list(),
        }
        return ( 'console/panes/hi_grid_side.html', context )
 

from django import template

from hi.simulator.profile.profile_manager import ProfileManager

from ..apps import NwsWeatherSimConfig
from ..models import NwsSimAlert

register = template.Library()


@register.simple_tag
def nws_sim_alert_list():
    """Alerts under NWS's currently-selected profile, newest first."""
    current_profile = ProfileManager().get_current( NwsWeatherSimConfig.name )
    return list(
        NwsSimAlert.objects
        .filter( sim_profile = current_profile )
        .order_by( '-created_datetime' )
    )

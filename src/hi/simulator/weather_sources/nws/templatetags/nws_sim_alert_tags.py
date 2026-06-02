from django import template

from hi.simulator.profile.profile_manager import ProfileManager

from ..apps import NwsWeatherSimConfig
from ..forms import NwsSimConditionsForm
from ..models import NwsSimAlert
from ..views import get_current_conditions

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


@register.simple_tag
def nws_sim_conditions_form():
    """Conditions/forecast form bound to the current-profile state."""
    return NwsSimConditionsForm( instance = get_current_conditions() )

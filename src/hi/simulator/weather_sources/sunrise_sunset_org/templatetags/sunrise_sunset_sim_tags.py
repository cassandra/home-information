from django import template

from ..forms import SunriseSunsetSimStateForm
from ..views import get_current_state

register = template.Library()


@register.simple_tag
def sunrise_sunset_sim_form():
    """Form bound to the current-profile state, for the inline tab pane."""
    return SunriseSunsetSimStateForm( instance = get_current_state() )

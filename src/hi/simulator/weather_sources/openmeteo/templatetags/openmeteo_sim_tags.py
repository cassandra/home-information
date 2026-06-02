from django import template

from ..forms import OpenMeteoSimStateForm
from ..views import get_current_state

register = template.Library()


@register.simple_tag
def openmeteo_sim_form():
    """Form bound to the current-profile state, for the inline tab pane."""
    return OpenMeteoSimStateForm( instance = get_current_state() )

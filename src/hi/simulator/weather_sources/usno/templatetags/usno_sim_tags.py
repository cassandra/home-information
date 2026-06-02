from django import template

from ..forms import UsnoSimStateForm
from ..views import get_current_state

register = template.Library()


@register.simple_tag
def usno_sim_form():
    """Form bound to the current-profile state, for the inline tab pane."""
    return UsnoSimStateForm( instance = get_current_state() )

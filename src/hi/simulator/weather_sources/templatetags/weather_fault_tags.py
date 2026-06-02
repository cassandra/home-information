from django import template

from hi.simulator.fault_injection import FaultMode

from ..fault_state import get_fault_mode

register = template.Library()


@register.inclusion_tag( 'weather_sources/panes/fault_mode_form.html' )
def weather_fault_mode_form( short_name ):
    """Render a source's inline fault-mode dropdown (current selection +
    choices). Shares its template with the set-view's async re-render."""
    return {
        'short_name': short_name,
        'current': get_fault_mode( short_name ),
        'choices': list( FaultMode ),
    }

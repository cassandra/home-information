from django import template
from django.template.loader import get_template

from hi.apps.entity.models import EntityState

register = template.Library()


@register.simple_tag( takes_context = True )
def render_state_value_text( context, entity_state : EntityState, value : str ):
    """Render the formatted display text for a single EntityState value.

    Resolves ``sense/panes/value_text_{state_type}.html`` for the
    entity_state's type, falling back to
    ``sense/panes/value_text_default.html``. The dispatched template
    emits the formatted display text only — no outer wrapping, no
    polling markers, no click-through. The caller (e.g., the live
    sensor row or the per-state history row) supplies whatever
    outer chrome is appropriate for its context.

    This is the read-only value-display analogue of
    ``include_controller_widget`` (which dispatches interactive
    controller widgets); both are template-layer dispatches kept
    off the domain enum to avoid coupling
    ``hi.apps.entity.enums.EntityStateType`` to frontend template
    directory conventions."""
    state_type_name = entity_state.entity_state_type.name.lower()
    template_name = f'sense/panes/value_text_{state_type_name}.html'
    try:
        template_obj = get_template( template_name )
    except Exception:
        template_obj = get_template( 'sense/panes/value_text_default.html' )
    flat = context.flatten()
    flat[ 'entity_state' ] = entity_state
    flat[ 'value' ] = value
    return template_obj.render( flat )


@register.simple_tag
def state_value_status( entity_state : EntityState, value : str ) -> str:
    """The CSS status token for a single EntityState value, via the same
    dispatch the live display uses (``EntityStateDisplayData``), so a
    bucketed type (TEMPERATURE, BATTERY, dimmer, position) colors the
    same way it does on the SVG icon / status panels. Falls back to the
    raw value when the dispatch yields no token (unrecognized value), so
    callers can always render a ``status="..."`` attribute.

    Imported lazily to keep the sense template tags free of a load-time
    dependency on the monitor display layer."""
    from hi.apps.monitor.display_data import EntityStateDisplayData
    svg_status_style = EntityStateDisplayData.for_value( entity_state, value ).svg_status_style
    if svg_status_style and svg_status_style.status_value:
        return svg_status_style.status_value
    return value

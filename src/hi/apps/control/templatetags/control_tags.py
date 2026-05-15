from django import template
from django.template.loader import get_template

from hi.apps.control.models import Controller

register = template.Library()


@register.simple_tag( takes_context = True )
def include_controller_widget( context, controller : Controller ):
    """Render the interactive controller widget for ``controller``.

    Resolves ``control/panes/controller_{state_type}.html`` for the
    controller's EntityStateType, falling back to
    ``control/panes/controller_default.html``. This is the per-state-type
    widget *layout* used by the EntityStatus row-list — a template-layer
    concern, not a model-layer one (it assumes an inline form snippet
    inside a row). The read-only value-display analogue is
    ``sense_tags.render_state_value_text``."""
    state_type_name = controller.entity_state.entity_state_type.name.lower()
    template_name = f'control/panes/controller_{state_type_name}.html'
    try:
        template_obj = get_template( template_name )
    except Exception:
        template_obj = get_template( 'control/panes/controller_default.html' )
    return template_obj.render( context.flatten() )

from django import template
from django.template.loader import get_template


register = template.Library()


@register.simple_tag( takes_context = True )
def include_panel( context, entity_panel_data ):
    """Render ``entity_panel_data.panel_template`` with the parent context
    flattened and ``entity_panel_data.panel_context`` merged on top. The
    view layer resolves which panel to render; this tag handles only the
    context flattening that template-side ``{% include %}`` cannot express."""
    flat = context.flatten()
    flat.update( entity_panel_data.panel_context )
    return get_template( entity_panel_data.panel_template ).render( flat )

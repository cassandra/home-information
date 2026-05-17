from django import template
from django.template.loader import get_template


register = template.Library()


@register.simple_tag( takes_context = True )
def include_panel( context, state_panel_data ):
    """Render ``state_panel_data.panel_template`` with the parent context
    flattened and ``state_panel_data.panel_context`` merged on top. The
    view layer resolves which panel to render; this tag handles only the
    context flattening that template-side ``{% include %}`` cannot express.
    The parent's ``request`` is passed through so the inner template
    renders under a RequestContext (re-running context processors)."""
    flat = context.flatten()
    flat.update( state_panel_data.panel_context )
    return get_template( state_panel_data.panel_template ).render(
        flat, request = context.get( 'request' ),
    )

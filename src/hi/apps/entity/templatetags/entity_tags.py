from django import template

from hi.apps.entity.enums import EntityStateValue

register = template.Library()


@register.filter
def value_label( value ):
    """Resolve a stored ``EntityStateValue`` wire string (the
    lowercased enum name, e.g., ``'smoke_detected'``) to its
    human-readable label (e.g., ``'Smoke Detected'``). Returns
    the input unchanged when it doesn't match an enum member —
    keeps numeric / free-form values rendering as-is."""
    if not value:
        return value
    try:
        return EntityStateValue.from_name( value ).label
    except ValueError:
        return value

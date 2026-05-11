from django import template

from hi.apps.entity.enums import EntityStateValue

register = template.Library()


@register.filter
def value_label( value ):
    """Resolve a stored wire value to its display label via
    ``EntityStateValue.to_display_label`` — enum members return
    their authoritative label, free-form names get humanized,
    numeric values pass through."""
    return EntityStateValue.to_display_label( value )

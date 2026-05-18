from django import template

from hi.apps.entity.enums import EntityStateValue

register = template.Library()


@register.filter
def value_label( value ):
    """Resolve a stored EntityState value to its display label via
    ``EntityStateValue.to_display_label`` — enum members return
    their authoritative label, free-form names get humanized,
    numeric values pass through."""
    return EntityStateValue.to_display_label( value )


@register.simple_tag
def entity_display_svg_icon_item( entity ):
    """Build the display-only SvgIconItem for ``entity`` from the
    factory. Useful for templates that need the icon (e.g. the shared
    entity-modal subheader) but whose views don't otherwise carry the
    icon item in their context."""
    from hi.apps.location.svg_item_factory import SvgItemFactory
    if not entity:
        return None
    return SvgItemFactory().get_display_only_svg_icon_item( entity = entity )

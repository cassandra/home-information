from django import template

register = template.Library()


@register.simple_tag
def get_attribute_history_url(attribute):
    """
    Get the correct history URL name for the given attribute.
    Uses the attribute's get_history_url_name() method.
    """
    if not attribute:
        return ''
    
    try:
        return attribute.get_history_url_name()
    except (AttributeError, NotImplementedError):
        return ''


@register.simple_tag
def get_attribute_restore_url(attribute):
    """
    Get the correct restore URL name for the given attribute.
    Uses the attribute's get_restore_url_name() method.
    """
    if not attribute:
        return ''
    
    try:
        return attribute.get_restore_url_name()
    except (AttributeError, NotImplementedError):
        return ''

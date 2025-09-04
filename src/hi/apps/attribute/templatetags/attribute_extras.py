from django import template

register = template.Library()


@register.filter
def attribute_preview(value, max_chars=60):
    """
    Create a compact preview of an attribute value for history display.
    
    For large or multiline values, shows first line (truncated if needed) 
    with indicators for additional content.
    
    Args:
        value: The attribute value to preview
        max_chars: Maximum characters to show from first line (default 60)
    
    Returns:
        String preview with optional indicators like "... +2 lines, +45 chars"
    """
    if not value:
        return "(empty)"
    
    # Convert to string and split into lines
    value_str = str(value)
    lines = value_str.split('\n')
    first_line = lines[0]
    
    # Handle first line truncation
    if len(first_line) > max_chars:
        preview = first_line[:max_chars] + "..."
        extra_chars = len(first_line) - max_chars
    else:
        preview = first_line
        extra_chars = 0
    
    # Calculate additional content indicators
    extra_lines = len(lines) - 1
    indicators = []
    
    if extra_lines > 0:
        indicators.append(f"+{extra_lines} line{'s' if extra_lines != 1 else ''}")
    
    if extra_chars > 0:
        indicators.append(f"+{extra_chars} char{'s' if extra_chars != 1 else ''}")
    
    # Add indicators if there's additional content
    if indicators:
        preview += f" ... {', '.join(indicators)}"
    
    return preview


@register.filter
def file_title_field_name(attr_item_context, attribute_id):
    """
    Generate the form field name for file title editing.
    
    Usage in template: {{ attr_item_context|file_title_field_name:attribute.id }}
    
    Args:
        attr_item_context: AttributeItemEditContext instance
        attribute_id: The attribute's ID
        
    Returns:
        str: Form field name like 'file_title_1_23'
    """
    return attr_item_context.file_title_field_name(attribute_id)


@register.filter
def history_target_id(attr_item_context, attribute_id):
    """
    Generate the DOM ID for attribute history container.
    
    Usage in template: {{ attr_item_context|history_target_id:attribute.id }}
    
    Args:
        attr_item_context: AttributeItemEditContext instance
        attribute_id: The attribute's ID
        
    Returns:
        str: DOM ID like 'hi-entity-attr-history-1-23'
    """
    return attr_item_context.history_target_id(attribute_id)


@register.filter
def history_toggle_id(attr_item_context, attribute_id):
    """
    Generate the DOM ID for history toggle/collapse target.
    
    Usage in template: {{ attr_item_context|history_toggle_id:attribute.id }}
    
    Args:
        attr_item_context: AttributeItemEditContext instance
        attribute_id: The attribute's ID
        
    Returns:
        str: DOM ID like 'history-extra-1-23'
    """
    return attr_item_context.history_toggle_id(attribute_id)


@register.simple_tag
def attr_history_url(attr_item_context, attribute_id):
    """
    Generate URL for attribute history view with correct parameter names.
    
    Usage in template: {% attr_history_url attr_item_context attribute.id %}
    
    Args:
        attr_item_context: AttributeItemEditContext instance
        attribute_id: The attribute's ID
        
    Returns:
        str: URL for history view
    """
    from django.urls import reverse
    url_name = attr_item_context.history_url_name
    params = {
        attr_item_context.owner_id_param_name: attr_item_context.owner_id,
        'attribute_id': attribute_id
    }
    return reverse(url_name, kwargs=params)


@register.simple_tag
def attr_restore_url(attr_item_context, attribute_id, history_id):
    """
    Generate URL for attribute restore view with correct parameter names.
    
    Usage in template: {% attr_restore_url attr_item_context attribute.id history_record.pk %}
    
    Args:
        attr_item_context: AttributeItemEditContext instance
        attribute_id: The attribute's ID
        history_id: The history record's ID
        
    Returns:
        str: URL for restore view
    """
    from django.urls import reverse
    url_name = attr_item_context.restore_url_name
    params = {
        attr_item_context.owner_id_param_name: attr_item_context.owner_id,
        'attribute_id': attribute_id,
        'history_id': history_id
    }
    return reverse(url_name, kwargs=params)

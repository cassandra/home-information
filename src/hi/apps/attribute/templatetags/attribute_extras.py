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
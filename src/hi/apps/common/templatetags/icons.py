"""
Icon template tags for consistent SVG icon rendering throughout the application.

This module provides template tags for rendering inline SVG icons with consistent
styling and accessibility features. All icons are self-contained (no external
dependencies) and integrate with the existing CSS variable system.

Usage:
    {% load icons %}
    {% icon "plus" size="md" color="primary" aria_label="Add item" %}
    {% icon "chevron-up" %}
"""

from django import template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

register = template.Library()

# Define available icon names to prevent arbitrary file inclusion
AVAILABLE_ICONS = {
    'camera',
    'cancel',
    'check-circle',
    'chevron-double-left',
    'chevron-double-right',
    'chevron-down',
    'chevron-left',
    'chevron-right',
    'chevron-up',
    'clock',
    'close',
    'cloud',
    'collection',
    'delete',
    'disabled',
    'edit',
    'exclamation-circle',
    'eye',
    'eye-off',
    'history',
    'home',
    'info-circle',
    'layers',
    'lightbulb',
    'lock',
    'map-pin',
    'minus-circle',
    'move',
    'path',
    'play',
    'plug',
    'plus',
    'question-circle',
    'rocket',
    'rotate',
    'save',
    'settings',
    'shield',
    'sync',
    'tasks',
    'times-circle',
    'unlock',
    'upload',
    'video',
    'view',
    'warning',
    'zoom',
}

# Define available sizes
ICON_SIZES = {'sm', 'md', 'lg', 'xl'}

# Define available semantic colors (matching CSS variables)
ICON_COLORS = {
    'primary',
    'secondary', 
    'success',
    'warning',
    'error',
    'muted'
}


@register.simple_tag
def icon(name, size='md', color=None, aria_label=None, title=None, css_class=''):
    """
    Render an inline SVG icon with consistent styling and accessibility.
    
    Args:
        name (str): Icon name (must be in AVAILABLE_ICONS)
        size (str): Icon size ('sm', 'md', 'lg', 'xl'). Default: 'md'
        color (str): Semantic color ('primary', 'secondary', etc.). Default: None
        aria_label (str): Accessibility label. If provided, icon is meaningful. 
                         If None, icon is decorative (aria-hidden="true")
        title (str): Tooltip text. Default: None
        css_class (str): Additional CSS classes. Default: ''
    
    Returns:
        SafeString: Rendered SVG icon HTML
        
    Raises:
        template.TemplateSyntaxError: If icon name is not available
    """
    
    # Validate icon name
    if name not in AVAILABLE_ICONS:
        raise template.TemplateSyntaxError(
            f'Icon "{name}" is not available. '
            f'Available icons: {", ".join(sorted(AVAILABLE_ICONS))}'
        )
    
    # Validate size
    if size not in ICON_SIZES:
        size = 'md'  # Default fallback
    
    # Validate color
    if color and color not in ICON_COLORS:
        color = None  # Invalid color, use default
    
    # Build CSS classes
    classes = ['hi-icon', f'hi-icon-{size}']
    
    if color:
        classes.append(f'hi-icon-{color}')
    
    if css_class:
        classes.append(css_class)
    
    class_attr = ' '.join(classes)
    
    # Build accessibility attributes
    accessibility_attrs = []
    
    if aria_label:
        # Meaningful icon - has semantic meaning
        accessibility_attrs.append(f'aria-label="{aria_label}"')
        accessibility_attrs.append('role="img"')
    else:
        # Decorative icon - no semantic meaning
        accessibility_attrs.append('aria-hidden="true"')
    
    if title:
        accessibility_attrs.append(f'title="{title}"')
    
    accessibility_str = ' '.join(accessibility_attrs)
    
    try:
        # Load the specific icon template
        icon_template = get_template(f'icons/{name}.html')
        
        # Create context for the icon template
        icon_context = {
            'class_attr': class_attr,
            'accessibility_attrs': accessibility_str,
        }
        
        # Render the icon template
        rendered_icon = icon_template.render(icon_context)
        
        return mark_safe(rendered_icon)
        
    except template.TemplateDoesNotExist:
        # Fallback if icon template doesn't exist
        return mark_safe(
            f'<span class="{class_attr}" {accessibility_str}>[{name}]</span>'
        )


@register.simple_tag  
def icon_list():
    """
    Return a sorted list of available icon names.
    Useful for documentation or debugging.
    
    Returns:
        list: Sorted list of available icon names
    """
    return sorted(AVAILABLE_ICONS)


@register.filter
def has_icon(name):
    """
    Template filter to check if an icon is available.
    
    Args:
        name (str): Icon name to check
        
    Returns:
        bool: True if icon is available, False otherwise
    """
    return name in AVAILABLE_ICONS

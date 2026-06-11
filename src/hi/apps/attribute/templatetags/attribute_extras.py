import re
from urllib.parse import urlparse

from django import template
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Schemes are split by URI shape so both the validator and the
# free-text regex can be driven from one list. To add a scheme, add it
# to whichever group matches its syntax — _URL_IN_TEXT_PATTERN and
# _is_valid_url automatically pick it up.
#
# Netloc-form (``scheme://netloc/...``): http, https, rtsp.
# Path-only-form (``scheme:path``, no ``//``): mailto, tel, sms.
#
# Note on rtsp: most browsers don't open it natively — clicking only
# works for users with a registered handler (e.g., VLC). Keeping it
# linkable lets users right-click → copy URL.
_NETLOC_SCHEMES = ( 'http', 'https', 'rtsp' )
_PATH_ONLY_SCHEMES = ( 'mailto', 'tel', 'sms' )
_LINKABLE_URL_SCHEMES = frozenset( _NETLOC_SCHEMES + _PATH_ONLY_SCHEMES )

# One regex finds every linkable URL form in free text. Built from the
# scheme lists so the allowlist and the matcher can never drift.
_URL_IN_TEXT_PATTERN = re.compile(
    r'(?:(?:%s)://|(?:%s):)[^\s<>"\']+' % (
        '|'.join( _NETLOC_SCHEMES ),
        '|'.join( _PATH_ONLY_SCHEMES ),
    )
)

_TRAILING_PUNCTUATION = '.,;:!?)]}'


def _is_valid_url(value):
    """Return True when value is a linkable URL.

    Netloc-form schemes (http, https, rtsp) require a non-empty
    ``netloc`` — single-label intranet hostnames (e.g.
    ``http://cassandra:4100/…``) are accepted; Django's URLValidator
    rejects those because they lack a TLD, but they're common on LANs.

    Path-only schemes (mailto, tel, sms) require a non-empty ``path``
    (the email address / phone number), since they carry no netloc.
    """
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    scheme = parsed.scheme
    if scheme in _NETLOC_SCHEMES:
        return bool(parsed.netloc)
    if scheme in _PATH_ONLY_SCHEMES:
        return bool(parsed.path)
    return False


def _split_url_and_trailing_punctuation(candidate):
    """Split common trailing punctuation from URL candidates."""
    trailing = []
    trimmed = candidate

    while trimmed and trimmed[-1] in _TRAILING_PUNCTUATION:
        trailing.append(trimmed[-1])
        trimmed = trimmed[:-1]

    return trimmed, ''.join(reversed(trailing))


def _iter_valid_url_segments(text):
    """Yield (start, end, valid_url, trailing_punctuation) for each valid URL."""
    for match in _URL_IN_TEXT_PATTERN.finditer(text):
        raw_candidate = match.group(0)
        url_candidate, trailing = _split_url_and_trailing_punctuation(raw_candidate)

        if not url_candidate or not _is_valid_url(url_candidate):
            continue

        yield (match.start(), match.end(), url_candidate, trailing)


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


@register.simple_tag
def attr_restore_deleted_url(attr_item_context, attribute_id):
    """Generate URL for restoring soft-deleted attributes."""
    from django.urls import reverse
    url_name = attr_item_context.restore_deleted_url_name
    params = {
        attr_item_context.owner_id_param_name: attr_item_context.owner_id,
        'attribute_id': attribute_id,
    }
    return reverse(url_name, kwargs=params)


@register.simple_tag
def attr_restore_subsystem_url(attr_item_context):
    """
    Generate URL for attribute restore default view with correct parameter names.
    
    Usage in template: {% attr_restore_subsystem_url attr_item_context %}
    
    Args:
        attr_item_context: AttributeItemEditContext instance
        
    Returns:
        str: URL for restore all default view
    """
    from django.urls import reverse
    url_name = attr_item_context.restore_subsystem_url_name
    params = {
        attr_item_context.owner_id_param_name: attr_item_context.owner_id,
    }
    return reverse(url_name, kwargs=params)


@register.simple_tag
def attr_restore_all_url(attr_item_context):
    """
    Generate URL for attribute restore global default view.
    
    Usage in template: {% attr_restore_all_url attr_item_context %}
    
    Returns:
        str: URL for restore global default view
    """
    from django.urls import reverse
    url_name = attr_item_context.restore_all_url_name
    params = {
        attr_item_context.owner_id_param_name: attr_item_context.owner_id,
    }
    return reverse(url_name, kwargs=params)


@register.filter
def attribute_url(value):
    """
    Return a validated URL string when value is a URL, otherwise return empty string.

    This is intended for best-effort display-time detection without persisting
    any derived value in the database.
    """
    if value is None:
        return ""

    url_candidate = str(value).strip()
    if not url_candidate:
        return ""

    if not _is_valid_url(url_candidate):
        return ""

    return url_candidate


@register.filter
def attribute_text_has_url(value):
    """Return True when text contains at least one valid URL candidate."""
    if value is None:
        return False

    text_value = str(value)
    if not text_value:
        return False

    return any(True for _ in _iter_valid_url_segments(text_value))


@register.filter
def attribute_text_linkify(value):
    """
    Render text with inline clickable links while safely escaping non-URL text.

    Newlines are converted to <br> for read-mode display.
    """
    if value is None:
        return ""

    text_value = str(value)
    if text_value == "":
        return ""

    rendered_parts = []
    current_index = 0

    for start, end, valid_url, trailing in _iter_valid_url_segments(text_value):
        if start > current_index:
            rendered_parts.append(escape(text_value[current_index:start]))

        rendered_parts.append(
            format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                valid_url,
                valid_url,
            )
        )

        if trailing:
            rendered_parts.append(escape(trailing))

        current_index = end

    if current_index < len(text_value):
        rendered_parts.append(escape(text_value[current_index:]))

    html = ''.join(str(part) for part in rendered_parts).replace('\n', '<br>')
    return mark_safe(html)


@register.simple_tag
def ensure_thumbnail(attribute):
    """Render-time hook that triggers lazy thumbnail generation for a
    file attribute if one isn't already present. Use in display
    templates as ``{% ensure_thumbnail attribute %}`` ahead of any
    ``attribute.has_thumbnail`` / ``attribute.thumbnail_url`` reads.

    Renders nothing (the tag's side effect is the work). No-op for
    attributes that don't support thumbnails or already have one;
    generation failures are swallowed and the surrounding template
    falls back to its placeholder."""
    if hasattr( attribute, 'ensure_thumbnail' ):
        attribute.ensure_thumbnail()
    return ''

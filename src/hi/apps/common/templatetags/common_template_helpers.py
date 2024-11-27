import os
import urllib

from django import template
from django.conf import settings
from django.template import engines
from django.urls import reverse

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag
def pagination_url( page_number, existing_urlencoded_params = None ):

    params_dict = dict()
    if existing_urlencoded_params:
        for param_string in existing_urlencoded_params.split('&'):
            name, value = param_string.split( '=', 1 )
            params_dict[name] = value
            continue
    
    params_dict['page'] = page_number
    query_string = urllib.parse.urlencode( params_dict )
    return f'?{query_string}'


@register.simple_tag( takes_context = True )
def abs_url( context, view_name, *args, **kwargs ):
    return context['request'].build_absolute_uri(
        reverse(view_name, args=args, kwargs=kwargs)
    )


@register.filter
def leading_zeroes( value, desired_digits ):
    try:
        value = round(value)
    except ( TypeError, ValueError, OverflowError ):
        pass
    try:
        value = int(value)
    except ( TypeError, ValueError, OverflowError ):
        return ''
    value = str(value)
    return value.zfill(int(desired_digits))


@register.filter
def digit_count( value ):
    try:
        value = round(value)
    except ( TypeError, ValueError, OverflowError ):
        pass
    try:
        value = int(value)
    except ( TypeError, ValueError, OverflowError ):
        return 0
    return len(str(value))


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag( takes_context = True )
def include_media_template( context, file_path ):
    """
    Load a file from MEDIA_ROOT, treat it as a Django template,
    and render it with the current context.
    """
    if not file_path:
        return 'Template file path not defined.'
    
    full_path = os.path.join( settings.MEDIA_ROOT, file_path )

    if not os.path.exists(full_path):
        return f'Template file not found: {full_path}'

    with open(full_path, 'r') as file:
        file_content = file.read()

    template_engine = engines['django']
    template_obj = template_engine.from_string(file_content)

    context_dict = context.flatten()
    return template_obj.render(context_dict)

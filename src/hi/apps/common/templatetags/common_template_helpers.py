import urllib

from django import template
from django.conf import settings
from django.urls import reverse

register = template.Library()


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

from django import template

from hi.apps.console import device_markup

register = template.Library()


@register.simple_tag
def external_link_attrs():
    return device_markup.external_link_attrs()

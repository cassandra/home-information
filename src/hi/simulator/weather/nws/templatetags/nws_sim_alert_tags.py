from django import template

from ..models import NwsSimAlert

register = template.Library()


@register.simple_tag
def nws_sim_alert_list():
    return list( NwsSimAlert.objects.all().order_by( '-created_datetime' ) )

from typing import List

from django.http import HttpRequest
from django.template.loader import get_template

from .alert import Alert


class AlertHelpers:

    ALERT_LIST_BANNER_TEMPLATE_NAME = 'alert/panes/alert_banner_content.html'

    @classmethod
    def alert_list_to_html_str( cls,
                                request     : HttpRequest,
                                alert_list  : List[ Alert ] ) -> str:
        context = { 'alert_list': alert_list }
        template = get_template( cls.ALERT_LIST_BANNER_TEMPLATE_NAME )
        content = template.render( context, request = request )
        return content

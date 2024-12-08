from django.http import Http404
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.constants import DIVID
from hi.hi_async_view import HiModalView

from .alert_helpers import AlertHelpers
from .alert_manager import AlertManager


class AlertAcknowledgeView( View ):

    def post( self, request, *args, **kwargs ):
        alert_id = kwargs.get( 'alert_id' )
        alert_manager = AlertManager()
        try:
            alert_manager.acknowledge_alert( alert_id = alert_id )
        except KeyError:
            raise Http404( 'Unknown alert.' )

        alert_list_html_str = AlertHelpers.alert_list_to_html_str(
            request = request,
            alert_list = alert_manager.unacknowledged_alert_list,
        )
        return antinode.response(
            insert_map = {
                DIVID['ALERT_BANNER_CONTAINER']: alert_list_html_str
            },
        )


class AlertDetailsView( HiModalView ):
    pass


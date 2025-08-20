from django.http import Http404
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.constants import DIVID
from hi.hi_async_view import HiModalView

from .alert_helpers import AlertHelpers
from .alert_mixins import AlertMixin


class AlertAcknowledgeView( View, AlertMixin ):

    def post( self, request, *args, **kwargs ):
        alert_id = kwargs.get( 'alert_id' )
        alert_manager = self.alert_manager()
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
                DIVID['ALERT_BANNER_CONTENT']: alert_list_html_str
            },
        )


class AlertDetailsView( HiModalView, AlertMixin ):

    def get_template_name( self ) -> str:
        return 'alert/modals/alert_details.html'

    def get( self, request, *args, **kwargs ):
        alert_id = kwargs.get( 'alert_id' )
        alert_manager = self.alert_manager()
        try:
            alert = alert_manager.get_alert( alert_id = alert_id )
        except KeyError:
            raise Http404( 'Unknown alert.' )

        # Prepare visual content data for template
        visual_content = self._get_first_visual_content( alert )

        context = {
            'alert': alert,
            'alert_visual_content': visual_content,
        }
        return self.modal_response( request, context )

    def _get_first_visual_content( self, alert ):
        """
        Find the first image/video content from any alarm in the alert.
        Returns dict with image info or None if no visual content found.
        """
        for alarm in alert.alarm_list:
            for source_details in alarm.source_details_list:
                if source_details.image_url:
                    return {
                        'image_url': source_details.image_url,
                        'alarm': alarm,
                        'is_from_latest': alarm == alert.alarm_list[0] if alert.alarm_list else False,
                    }
        return None
        


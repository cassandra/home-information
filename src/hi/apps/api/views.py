from datetime import datetime
import json
import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponse
from django.views.generic import View

from hi.apps.alert.alert_manager import AlertManager
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.security.security_manager import SecurityManager

logger = logging.getLogger(__name__)


class StatusView( View ):

    ServerStartTimestampAttr = 'startTimestamp'
    ServerTimestampAttr = 'timestamp'
    LastServerTimestampAttr = 'lastTimestamp'
    AlertStatusDataAttr = 'alertData'
    CssClassUpdateMapAttr = 'cssClassUpdateMap'
    IdReplaceUpdateMapAttr = 'idReplaceUpdateMap'

    def get( self, request, *args, **kwargs ):

        last_server_timestamp = request.GET.get( self.LastServerTimestampAttr )
        last_server_datetime = None
        if last_server_timestamp:
            try:
                last_server_datetime = datetime.fromisoformat(
                    last_server_timestamp.replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                msg = f'Missing or invalid date/time format "{last_server_timestamp}".'
                logger.warning( msg )
                raise BadRequest( msg )
            
        server_start_datetime = SettingsManager().get_server_start_datetime()
        server_datetime = datetimeproxy.now()

        alert_status_data = AlertManager().get_alert_status_data(
            last_alert_status_datetime = last_server_datetime,
        )

        id_replace_map = dict()
        id_replace_map.update( SecurityManager().get_status_id_replace_map( request = request ) )

        css_class_update_map = dict()
        css_class_update_map.update( StatusDisplayManager().get_status_css_class_update_map() )

        data = {
            self.ServerStartTimestampAttr: server_start_datetime.isoformat(),
            self.ServerTimestampAttr: server_datetime.isoformat(),
            self.AlertStatusDataAttr: alert_status_data.to_dict( request = request ),
            self.IdReplaceUpdateMapAttr: id_replace_map,
            self.CssClassUpdateMapAttr: css_class_update_map,
        }
        return HttpResponse(
            json.dumps(data),
            content_type='application/json',
            status = 200,
        )

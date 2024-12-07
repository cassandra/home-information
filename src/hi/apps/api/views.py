from datetime import datetime
import json
import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponse
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.monitor.status_display_data import StatusDisplayData


logger = logging.getLogger(__name__)


class StatusView( View ):

    ServerStartTimestampAttr = 'startTimestamp'
    ServerTimestampAttr = 'timestamp'
    LastServerTimestampParam = 'lastTimestamp'
    CssClassUpdateMap = 'cssClassUpdateMap'

    def get( self, request, *args, **kwargs ):

        last_server_timestamp = request.GET.get( self.LastServerTimestampParam )
        last_server_datetime = None
        if last_server_timestamp:
            try:
                last_server_datetime = datetime.fromisoformat( last_server_timestamp.replace("Z", "+00:00") )
            except (TypeError, ValueError):
                msg = f'Missing or invalid date/time format "{last_server_timestamp}".'
                logger.warning( msg )
                raise BadRequest( msg )
            
        server_start_datetime = SettingsManager().get_server_start_datetime()
        server_datetime = datetimeproxy.now()

        entity_state_status_data_list = StatusDisplayManager().get_all_entity_state_status_data_list()
        status_display_data_list = [ StatusDisplayData(x) for x in entity_state_status_data_list ]

        css_class_update_map = dict()
        for status_display_data in status_display_data_list:
            if status_display_data.should_skip:
                continue
            css_class_update_map[status_display_data.css_class] = status_display_data.attribute_dict
            continue
        
        data = {
            self.ServerStartTimestampAttr: server_start_datetime.isoformat(),
            self.ServerTimestampAttr: server_datetime.isoformat(),
            self.CssClassUpdateMap: css_class_update_map,
        }
        return HttpResponse(
            json.dumps(data),
            content_type='application/json',
            status = 200,
        )

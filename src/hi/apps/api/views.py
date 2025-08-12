from datetime import datetime
import hashlib
import json
import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponse
from django.views.generic import View

from hi.apps.alert.alert_mixins import AlertMixin
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.security.security_mixins import SecurityMixin
from hi.apps.weather.weather_mixins import WeatherMixin

logger = logging.getLogger(__name__)


class StatusView( View, AlertMixin, SecurityMixin, SettingsMixin, WeatherMixin ):

    ServerStartTimestampAttr = 'startTimestamp'
    ServerTimestampAttr = 'timestamp'
    LastServerTimestampAttr = 'lastTimestamp'
    AlertStatusDataAttr = 'alertData'
    CssClassUpdateMapAttr = 'cssClassUpdateMap'
    IdReplaceUpdateMapAttr = 'idReplaceUpdateMap'
    IdReplaceHashMapAttr = 'idReplaceHashMap'

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
            
        server_start_datetime = self.settings_manager().get_server_start_datetime()
        server_datetime = datetimeproxy.now()

        alert_status_data = self.alert_manager().get_alert_status_data(
            last_alert_status_datetime = last_server_datetime,
        )

        id_replace_map = dict()
        id_replace_map.update( self.security_manager().get_status_id_replace_map( request = request ) )
        id_replace_map.update( self.weather_manager().get_status_id_replace_map( request = request ) )

        css_class_update_map = dict()
        css_class_update_map.update( StatusDisplayManager().get_status_css_class_update_map() )

        # Hash provided for client to prevent unneeded DOM updates since
        # they can interfer with user interactions.
        #
        id_replace_hash_map = dict()
        for id, html_text in id_replace_map.items():
            encoded_string = html_text.encode('utf-8')
            md5_hash = hashlib.md5(encoded_string)
            id_replace_hash_map[id] = md5_hash.hexdigest()
            continue
        
        data = {
            self.ServerStartTimestampAttr: server_start_datetime.isoformat(),
            self.ServerTimestampAttr: server_datetime.isoformat(),
            self.AlertStatusDataAttr: alert_status_data.to_dict( request = request ),
            self.CssClassUpdateMapAttr: css_class_update_map,
            self.IdReplaceUpdateMapAttr: id_replace_map,
            self.IdReplaceHashMapAttr: id_replace_hash_map,
        }
        return HttpResponse(
            json.dumps(data),
            content_type='application/json',
            status = 200,
        )

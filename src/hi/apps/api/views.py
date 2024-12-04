import json
import logging

from django.http import HttpResponse
from django.views.generic import View

from hi.apps.monitor.status_data_helpers import StatusDataHelper
from hi.apps.monitor.status_display_data import StatusDisplayData


logger = logging.getLogger(__name__)


class StatusView( View ):

    CssClassUpdateMap = 'cssClassUpdateMap'

    def get( self, *args, **kwargs ):

        entity_state_status_data_list = StatusDataHelper().get_entity_state_status_data_list()
        status_display_data_list = [ StatusDisplayData(x) for x in entity_state_status_data_list ]

        css_class_update_map = dict()
        for status_display_data in status_display_data_list:
            if status_display_data.should_skip:
                continue
            css_class_update_map[status_display_data.css_class] = status_display_data.attribute_dict
            continue
        
        data = {
            self.CssClassUpdateMap: css_class_update_map,
        }
        return HttpResponse(
            json.dumps(data),
            content_type='application/json',
            status = 200,
        )

    
    

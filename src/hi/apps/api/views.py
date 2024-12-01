import json
import logging

from django.http import HttpResponse
from django.views.generic import View

from hi.apps.monitor.status_display_helpers import StatusDisplayStatusViewHelper


logger = logging.getLogger(__name__)


class StatusView( View ):

    CssClassUpdateMap = 'cssClassUpdateMap'

    def get( self, *args, **kwargs ):
        status_display_data_list = StatusDisplayStatusViewHelper().get_status_display_data()

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

    
    

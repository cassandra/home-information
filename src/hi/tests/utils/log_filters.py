import logging
import re

from django.conf import settings
from django.urls import resolve


class SuppressSelectRequestEndpointsFilter(logging.Filter):
    """Filter out logs for specific URL names instead of hardcoded paths."""

    URL_NAMES_TO_FILTER = {
        "api_status",
    }

    def filter( self, record ):
        if not settings.SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING:
            return True
        try:
            if not hasattr(record, "args") or ( len(record.args) < 1 ):
                return True
        
            request_line = record.args[0]

            if not isinstance( request_line, str ):
                # Sometimes it apears to be a PosixPath, but for requests it is a string.
                return True
            
            match = re.match( r'^[A-Z]+ (/[^ ?]*)', request_line )
            if not match:
                return True

            request_path = match.group(1)
            match = resolve( request_path )
            if match.url_name in self.URL_NAMES_TO_FILTER:
                return False

        except Exception:
            pass
        
        return True

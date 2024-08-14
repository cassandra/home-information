import logging

from django.db import connection

from .redis_client import get_redis_client

logger = logging.getLogger(__name__)


def do_healthcheck( db_layer = True, cache_layer = True ):

    result = { 'status_code': 200 }

    if db_layer:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            result['database'] = 'ok'
        except Exception as e:
            result['database'] = str(e)
            result['status_code'] = 500
            
    else:
        result['database'] = 'not-checked'

    if cache_layer:
        try:
            get_redis_client().ping()
            result['cache'] = 'ok'
        except Exception as e:
            result['cache'] = str(e)
            result['status_code'] = 500
   
    else:
        result['cache'] = 'not-checked'

    return result


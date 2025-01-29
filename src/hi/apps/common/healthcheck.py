from typing import Dict

from django.db import connection

from .redis_client import get_redis_client


def do_healthcheck( db_layer = True, cache_layer = True ) -> Dict[ str, str ]:

    status = {
        'is_healthy': True,
        'database': 'healthy',
        'cache': 'healthy',
    }
    if db_layer:
        try:
            connection.ensure_connection()
        except Exception as e:
            status['database'] = f'unhealthy: {str(e)}'
            status['is_healthy'] = False
    else:
        status['database'] = 'not-checked'

    if cache_layer:
        try:
            get_redis_client().ping()
        except Exception as e:
            status['cache'] = f'unhealthy: {str(e)}'
            status['is_healthy'] = False
    else:
        status['cache'] = 'not-checked'

    return status


# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

INSTALLED_APPS += [ 'hi.tests' ]

STATIC_ROOT = '/tmp/hi/static'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Since the API status gets polled frequently, this gums up the
    # terminal and make developing and debugging everything else more
    # unpleasant.
    #
    'filters': {
        'suppress_select_request_endpoints': {
            '()': 'hi.tests.utils.log_filters.SuppressSelectRequestEndpointsFilter',
        },
    },
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': [ 'suppress_select_request_endpoints' ],
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'hi.apps.alert': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.control': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.notify': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.monitor': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.sense': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.security': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.integrations': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.services.hass': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.services.zoneminder': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi': {
            'handlers': ['console' ],
            'level': 'INFO',
        },
    },
}

BASE_URL_FOR_EMAIL_LINKS = 'http:/127.0.0.1:8411/'

# Uncomment to suppress email sending and write to console.
#
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING = True
SUPPRESS_MONITORS = False

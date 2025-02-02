# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

INSTALLED_APPS += [ 'hi.tests' ]

ALLOWED_HOSTS = [
    '127.0.0.1',
    '192.168.100.6',
    '192.168.100.112',
    'localhost',
]

# Content Security Policy Settings for CSPMiddleware
#
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8008',
]
CSP_DEFAULT_SRC = (
    "'self'",
    'data:',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8008',
)
CSP_CONNECT_SRC = (
    "'self'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8008',
    "ws://127.0.0.1:8000",
    "ws://localhost:8000",
    'ws://192.168.100.6:8008',
    'ws://192.168.100.80:8000',
)
CSP_FRAME_SRC = [
    "'self'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8008',
    'https://player.vimeo.com',
]

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8008',
    'https://bordeaux:8443',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
)

CSP_MEDIA_SRC = [
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    'data:',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8008',
    'https://bordeaux:8443',
]

CSP_IMG_SRC = [
    "'self'",
    'data:',
    'https://bordeaux:8443',
]

CSP_CHILD_SRC = [
    "'self'",
]

CSP_FONT_SRC = [
    "'self'",
    'data:',
]

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
            '()': 'hi.log_filters.SuppressSelectRequestEndpointsFilter',
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

BASE_URL_FOR_EMAIL_LINKS = 'http:/127.0.0.1:8000/'

# Uncomment to suppress email sending and write to console.
#
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING = True
SUPPRESS_MONITORS = False

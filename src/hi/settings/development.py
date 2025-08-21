# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Override template options for development debugging
TEMPLATES[0]['OPTIONS'].update({
    'debug': True,
    #'string_if_invalid': 'INVALID_VARIABLE_%s',
})

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
        'suppress_pipeline_template_vars': {
            '()': 'hi.apps.common.log_filters.SuppressPipelineTemplateVarsFilter',
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
            'level': 'DEBUG',
            'propagate': False,
        },
        'hi.apps.control': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.console': {
            'handlers': ['console' ],
            'level': 'DEBUG',
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
        'hi.apps.weather': {
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
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',  # Changed from DEBUG to INFO to reduce verbose variable lookup messages
            'filters': ['suppress_pipeline_template_vars'],
            'propagate': False,
        },
    },
}

BASE_URL_FOR_EMAIL_LINKS = 'http:/127.0.0.1:8411/'

# Uncomment to suppress email sending and write to console.
#
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING = True
SUPPRESS_MONITORS = False

# ====================
# Development Testing Injection Points
# Enable/disable these here for frontend testing

# Allows injecting transient view data for testing auto-view functionality
DEBUG_FORCE_TRANSIENT_VIEW_OVERRIDE = False  # Set to True to enable

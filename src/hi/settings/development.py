# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Override template options for development debugging
TEMPLATES[0]['OPTIONS'].update({
    'debug': True,
    #'string_if_invalid': 'INVALID_VARIABLE_%s',
})

INSTALLED_APPS += [ 'hi.testing' ]

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
            '()': 'hi.testing.utils.log_filters.SuppressSelectRequestEndpointsFilter',
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
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.console': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.control': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.services.hass': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.integrations': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.location': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.monitor': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.notify': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.security': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.sense': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'hi.apps.weather': {
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
        'hi.state_trace': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
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

# Enables the simulator's Scenes "Clear States" action to make the status
# display drop sensor responses older than its cutoff (avoids waiting out the
# recent/past decay between sequence runs). Dev-only.
DEBUG_FORCE_SENSOR_RESPONSE_CUTOFF = True
# Shared cache key holding the "Clear States" cutoff epoch: the independent
# simulator process writes it; the main app reads it (DevInjectionManager
# .apply_sensor_response_cutoff). The *only* contract between the two processes
# for this feature — both inherit it here, so neither imports the other's code.
SENSOR_RESPONSE_CUTOFF_CACHE_KEY = 'hi.dev.sensor_response_cutoff'

# For testing UI error display of the various attribute editing form errors.
DEBUG_INJECT_ATTRIBUTE_FORM_ERRORS = False

# Per-state tracing for debugging value flow. Set
# ``DEBUG_TRACE_STATE = True`` and populate one or both id lists
# with the specific integration_names and/or HI EntityState PKs
# to instrument.
DEBUG_TRACE_STATE = False
DEBUG_TRACE_INTEGRATION_NAMES = [ ]  # strings / integration_key.name
DEBUG_TRACE_HI_ENTITY_STATE_IDS = [ ]  # ints / EntityState database ids

# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

STATIC_ROOT = '/tmp/hi/static'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'hi': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

BASE_URL_FOR_EMAIL_LINKS = 'http:/127.0.0.1:8411/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING = True
SUPPRESS_MONITORS = True

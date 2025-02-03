from .base import *

DEBUG = False

SITE_DOMAIN = 'python-causal-kingfish.ngrok-free.app'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'wordsacrossamerica.com',
    SITE_DOMAIN,
    '192.168.100.6',
]

CORS_ALLOWED_ORIGINS = [ 
    'http://127.0.0.1:9411',
    'http://localhost:9411',
]
CSP_DEFAULT_SRC = (
    "'self'",
    'data:',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
)
CSP_CONNECT_SRC = (
    "'self'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
)
CSP_FRAME_SRC = [
    "'self'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
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
]

CSP_IMG_SRC = [
    "'self'",
    'data:',
]

CSP_CHILD_SRC = [
    "'self'",
]

CSP_FONT_SRC = [
    "'self'",
    'data:',
]

STATICFILES_STORAGE = 'pipeline.storage.PipelineManifestStorage'
STATIC_ROOT = '/src/static'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {module} {process:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'hi': {
            'handlers': ['console' ],
            'level': 'INFO',
        },
    },
}

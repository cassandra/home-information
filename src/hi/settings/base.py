"""
Django settings for hi project.

Generated by 'django-admin startproject' using Django 4.2.15.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os

from .helpers import EnvironmentSettings

env_settings = EnvironmentSettings.get()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env_settings.SECRET_KEY

DJANGO_SUPERUSER_EMAIL = env_settings.DJANGO_SUPERUSER_EMAIL
DJANGO_SUPERUSER_PASSWORD = env_settings.DJANGO_SUPERUSER_PASSWORD

SITE_ID = env_settings.SITE_ID
SITE_DOMAIN = env_settings.SITE_DOMAIN
SITE_NAME = env_settings.SITE_NAME

ALLOWED_HOSTS = env_settings.ALLOWED_HOSTS

CORS_ALLOWED_ORIGINS = env_settings.CORS_ALLOWED_ORIGINS

CSP_DEFAULT_SRC = (
    "'self'",
    'data:',
) + env_settings.EXTRA_CSP_URLS

CSP_CONNECT_SRC = (
    "'self'",
) + env_settings.EXTRA_CSP_URLS

CSP_FRAME_SRC = (
    "'self'",
) + env_settings.EXTRA_CSP_URLS

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
) + env_settings.EXTRA_CSP_URLS

CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
) + env_settings.EXTRA_CSP_URLS

CSP_MEDIA_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    'data:',
) + env_settings.EXTRA_CSP_URLS

CSP_IMG_SRC = (
    "'self'",
    'data:',
) + env_settings.EXTRA_CSP_URLS

CSP_CHILD_SRC = (
    "'self'",
) + env_settings.EXTRA_CSP_URLS

CSP_FONT_SRC = (
    "'self'",
    'data:',
) + env_settings.EXTRA_CSP_URLS

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pipeline',
    'django.contrib.humanize',
    'constance',
    'custom',
    'hi.apps.common',
    'hi.apps.user',
    'hi.apps.config',
    'hi.apps.console',
    'hi.apps.attribute',
    'hi.apps.location',
    'hi.apps.entity',
    'hi.apps.collection',
    'hi.apps.sense',
    'hi.apps.control',
    'hi.apps.event',
    'hi.apps.notify',
    'hi.apps.alert',
    'hi.apps.security',
    'hi.apps.edit',
    'hi.apps.api',
    'hi.apps.monitor',
    'hi.integrations',
    'hi.services.zoneminder',
    'hi.services.hass',
]

MIDDLEWARE = [
    'csp.middleware.CSPMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'hi.middleware.ExceptionMiddleware',
    'hi.middleware.ViewMiddleware',
    'hi.apps.console.middleware.ConsoleLockMiddleware',
    'hi.apps.user.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'hi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ os.path.join(BASE_DIR, "templates") ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hi.context_processors.constants_context',
                'hi.apps.config.context_processors.settings_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'hi.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join( env_settings.DATABASES_NAME_PATH, 'hi.sqlite3' ),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_ROOT = env_settings.MEDIA_ROOT
MEDIA_URL = '/media/'

PIPELINE = {
    'DISABLE_WRAPPER': True,  # Important since some scripts assume global scope

    'CSS_COMPRESSOR': 'django_pipeline_csscompressor.CssCompressor',
    'JS_COMPRESSOR': None,
    
    'STYLESHEETS': {
        'css_head': {
            'source_filenames': (
                'bootstrap/css/bootstrap.css',
                'css/main.css',
            ),
            'output_filename': 'css/css_head.css',
        },
    },
    'JAVASCRIPT': {
        'js_before_content': {
            'source_filenames': (
                'js/jquery-3.7.0.min.js',
                'js/cookie.js',
                'js/antinode.js',
                'js/autosize.min.js',
                'js/main.js',
                'js/settings.js',
            ),
            'output_filename': 'js/js_before_content.js',
        },
        'js_after_content': {
            'source_filenames': (
                'js/popper.min.js',
                'bootstrap/js/bootstrap.js',
            ),
            'output_filename': 'js/js_after_content.js',
        },
        'js_hi_grid_content': {
            'source_filenames': (
                'js/svg-utils.js',
                'js/watchdog.js',
                'js/status.js',
                'js/edit.js',
                'js/edit-dragdrop.js',
                'js/svg-icon.js',
                'js/svg-path.js',
                'js/svg-location.js',
                'js/svg-event-listeners.js',
            ),
            'output_filename': 'js/js_hi_grid_content.js',
        },
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365  # in seconds
AUTO_LOGOUT = 60 * 24 * 365 * 100  # in minutes

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_DATABASE_CACHE_BACKEND = 'default'
CONSTANCE_DATABASE_PREFIX = 'constance:hi:'

CONSTANCE_CONFIG = {
    'DOWN_FOR_MAINTENANCE': ( False, 'Should we force the down for maintenance page to show?' ),
}

REDIS_HOST = env_settings.REDIS_HOST
REDIS_PORT = env_settings.REDIS_PORT
REDIS_KEY_PREFIX = env_settings.REDIS_KEY_PREFIX

CACHES = {
    'default': {
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': [
            f'redis://{REDIS_HOST}:{REDIS_PORT}',
        ],
        "KEY_PREFIX": f'main:{REDIS_KEY_PREFIX}',
    }
}


AUTH_USER_MODEL = "custom.CustomUser"
SUPPRESS_AUTHENTICATION = env_settings.SUPPRESS_AUTHENTICATION

# ====================
# Transactional Emails

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_SUBJECT_PREFIX = "%s " % env_settings.EMAIL_SUBJECT_PREFIX
DEFAULT_FROM_EMAIL = env_settings.DEFAULT_FROM_EMAIL
SERVER_EMAIL = env_settings.SERVER_EMAIL
FROM_EMAIL_NAME = "Home Information"

# Normal Settings
EMAIL_HOST = env_settings.EMAIL_HOST
try:
    EMAIL_PORT = env_settings.EMAIL_PORT
except (TypeError, ValueError):
    EMAIL_PORT = 587
    
EMAIL_HOST_USER = env_settings.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = env_settings.EMAIL_HOST_PASSWORD
EMAIL_TIMEOUT = 10  # In seconds

EMAIL_USE_TLS = env_settings.EMAIL_USE_TLS
EMAIL_USE_SSL = env_settings.EMAIL_USE_SSL
    
# Needed when sending emails in background tasks since HttpRequest not
# available. Override this for development/testing/staging.
#
BASE_URL_FOR_EMAIL_LINKS = 'http://{SITE_DOMAIN}'


# ====================
# Development-related Settings
# (override in development.py, not here)

# When tests functionality requires knowing if in unit test context.
UNIT_TESTING = False

# In development and debugging, because the background javascript is
# polling frequently, this clutters up the console with log messages which
# makes it hard to sort through the other things logging.  This allows
# suppressing those via a logging filter.  This only applies if the logging
# configuration is using that special filter (in hi.log_filters".
#
SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING = True

# In development and debugging, the debug noise and interference from the
# background periodic monitoring tasks can be a problem. This gives a way
# to turn them off with one setting.
#
SUPPRESS_MONITORS = False

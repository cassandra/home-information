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

from django.core.exceptions import ImproperlyConfigured


def get_env_variable( var_name, default=None ):
    try:
        return os.environ[var_name]
    except KeyError:
        if default:
            return default
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)

    
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = [
    '127.0.0.1',
    '192.168.100.2',
    '192.168.100.4',
    '192.168.100.6',
    'localhost',
]

CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.2:8111',
    'http://192.168.100.4:8111',
    'http://192.168.100.6:8111',
]
CSP_DEFAULT_SRC = (
    "'self'",
    'data:',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.2:8111',
    'http://192.168.100.4:8111',
    'http://192.168.100.6:8111',
)
CSP_CONNECT_SRC = (
    "'self'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.6:8111',
    "ws://127.0.0.1:8000",
    "ws://localhost:8000",
    'ws://192.168.100.6:8111',
    'ws://192.168.100.80:8000',
    )
CSP_FRAME_SRC = [
    "'self'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.2:8111',
    'http://192.168.100.4:8111',
    'http://192.168.100.6:8111',
]

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.100.2:8111',
    'http://192.168.100.4:8111',
    'http://192.168.100.6:8111',
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
    'http://192.168.100.2:8111',
    'http://192.168.100.4:8111',
    'http://192.168.100.6:8111',
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
    'hi.apps.common',
    'hi.apps.config',
    'hi.apps.location',
    'hi.apps.entity',
    'hi.apps.collection',
    'hi.apps.sense',
    'hi.apps.control',
    'hi.apps.edit',
    'hi.apps.api',
    'hi.integrations.core',
    'hi.integrations.zoneminder',
    'hi.integrations.hass',
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
    'hi.middleware.ViewMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'hi.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

HI_DB_PATH = get_env_variable('HI_DB_PATH')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join( HI_DB_PATH, 'hi.sqlite3' ),
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

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

MEDIA_ROOT = get_env_variable('HI_MEDIA_PATH')
MEDIA_URL = '/media/'

PIPELINE = {
    'DISABLE_WRAPPER': True,  # Important since some scripts assume global scope

    'CSS_COMPRESSOR': 'django_pipeline_csscompressor.CssCompressor',
    'JS_COMPRESSOR': 'pipeline.compressors.jsmin.JSMinCompressor',
    
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
                'js/antinode.js',
            ),
            'output_filename': 'js/js_before_content.js',
        },
        'js_after_content': {
            'source_filenames': (
                'js/cookie.js',
                'js/popper.min.js',
                'bootstrap/js/bootstrap.js',
            ),
            'output_filename': 'js/js_after_content.js',
        },
        'js_after_content_custom': {
            'source_filenames': (
                'js/main.js',
            ),
            'output_filename': 'js/js_after_content_custom.js',
        }
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


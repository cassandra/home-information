# -*- coding: utf-8 -*-
from .development import *

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pipeline',
    'django.contrib.humanize',
    
    'custom',
    'hi.apps.common',
    'hi.simulator',
    'hi.simulator.profile',
    'hi.simulator.services',
    'hi.simulator.weather_sources',
    'hi.simulator.settings',
    'hi.simulator.services.frigate',
    'hi.simulator.services.hass',
    'hi.simulator.services.homebox',
    'hi.simulator.services.paperless',
    'hi.simulator.services.immich',
    'hi.simulator.services.zoneminder',
    'hi.simulator.weather_sources.nws',
    'hi.simulator.weather_sources.openmeteo',
    'hi.simulator.weather_sources.sunrise_sunset_org',
    'hi.simulator.weather_sources.usno',
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

    'hi.simulator.middleware.NoStoreMiddleware',
    'hi.simulator.services.middleware.ServiceFaultInjectionMiddleware',
    'hi.simulator.weather_sources.middleware.WeatherFaultInjectionMiddleware',
]

ROOT_URLCONF = 'hi.simulator.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ os.path.join( BASE_DIR, "templates") ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join( ENV.DATABASES_NAME_PATH, 'simulator.sqlite3' ),
    }
}

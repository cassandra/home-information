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
    'hi.simulator.scenes',
    'hi.simulator.video_playback',
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


# Well-known directory of pre-canned camera clips. Each immediate subdirectory
# is a clip; its alphabetically-ordered ``*.jpg`` files are the frames. The
# subdirectory names become the camera ``live_clip`` / ``event_clip`` choices
# (scanned once at startup). Restart the simulator to pick up new clips.
SIMULATOR_VIDEO_DIR = str( BASE_DIR.parent.parent / 'data' / 'demo' / 'videos' )


# The LOGGING inherited from development wires a request-log suppression filter
# for the *main app's* endpoints (whose URL names don't resolve in this
# process). Swap in the simulator's own filter on the same console handler so
# the simulator's frequently-polled integration / weather / status endpoints
# stop flooding the dev console.
LOGGING[ 'filters' ][ 'suppress_select_request_endpoints' ][ '()' ] = (
    'hi.simulator.log_filters.SuppressSimulatorPollingFilter'
)

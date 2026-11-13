"""
WSGI config for hi project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

from django.core.wsgi import get_wsgi_application

from hi.environment.settings_module import require_settings_module

require_settings_module()

application = get_wsgi_application()

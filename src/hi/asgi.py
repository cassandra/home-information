"""
ASGI config for hi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

from django.core.asgi import get_asgi_application

from hi.environment.settings_module import require_settings_module

require_settings_module()

application = get_asgi_application()

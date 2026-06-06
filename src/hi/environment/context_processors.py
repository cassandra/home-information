from django.conf import settings
from django.urls import reverse

from hi.apps.console.console_helper import ConsoleSettingsHelper

from .client import ClientConfig


def client_config(request):
    """
    Provides client-side configuration to templates.
    
    Creates a structured configuration object that gets injected into
    JavaScript as HiClientConfig, providing a single source of truth for
    all client configuration needs.
    
    Fails fast on missing required data - no masking of interface problems.
    
    Returns:
        dict: Context variables for templates
    """
    config = ClientConfig(
        DEBUG = settings.DEBUG,
        ENVIRONMENT = settings.ENV.environment_name,
        VERSION = settings.ENV.VERSION,
        VIEW_MODE = str(request.view_parameters.view_mode),
        VIEW_TYPE = str(request.view_parameters.view_type) if request.view_parameters.view_type else None,
        IS_EDIT_MODE = request.view_parameters.is_editing,
        SVG_SNAP_GRID_PIXELS = request.view_parameters.svg_snap_grid_pixels,
        API_STATUS_URL = reverse( 'api_status' ),
        CONSOLE_UNLOCK_URL = reverse( 'console_unlock' ),
        API_STATUS_POLLING_INTERVAL_MS = ConsoleSettingsHelper().get_status_polling_interval_ms(),
    )
    
    return {
        'hi_client_config': config
    }

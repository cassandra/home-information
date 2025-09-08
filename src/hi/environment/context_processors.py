from django.conf import settings

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
    )
    
    return {
        'hi_client_config': config
    }

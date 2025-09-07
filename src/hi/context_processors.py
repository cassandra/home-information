from dataclasses import dataclass, asdict
from django.conf import settings

from .constants import DIVID


@dataclass
class ClientConfig:
    """Structured client-side configuration object.  Provides type safety
    and clear field definitions for server-to-client communication via
    template injected JS.  Consumed only by main.css.  ALl other JS look to
    main.css for relaying of these when needed.
    """
    DEBUG         : bool
    ENVIRONMENT   : str
    VERSION       : str
    VIEW_MODE     : str
    VIEW_TYPE     : str
    IS_EDIT_MODE  : bool
    
    def to_json_dict(self) -> dict:
        """
        Convert to dictionary suitable for JSON serialization in templates.
        Ensures proper JavaScript boolean/null handling.
        """
        return {
            key: (value if value is not None else 'null')
            for key, value in asdict(self).items()
        }


def constants_context(request):
    return {
        'DIVID': DIVID,
    }


def client_config(request):
    """
    Provides client-side configuration to templates.
    
    Creates a structured configuration object that gets injected into
    JavaScript as Hi.Config, providing a single source of truth for
    all client configuration needs.
    
    Fails fast on missing required data - no masking of interface problems.
    
    Returns:
        dict: Context variables for templates
    """
    # Core debug and environment settings - using namespaced settings for client export



    print( f'\n\n\nSETTINGS = {settings}\n\n\n' )


    

    
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

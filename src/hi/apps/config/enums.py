from hi.apps.common.enums import LabeledEnum


class ConfigPageType(LabeledEnum):
    """
    Defines those features that appear on the main config (admin) home
    page and links to their content.  Each tab in the config pane will
    have an enum entry.
    """
    
    def __init__( self,
                  label        : str,
                  description  : str,
                  url_name     : str ):
        super().__init__( label, description )
        self.url_name = url_name
        return

    SETTINGS                = ('Settings'        , ''   , 'config_settings' )
    EVENTS                  = ('Rules'           , ''   , 'event_definitions' )
    INTEGRATIONS_CONNECT    = ('Connectors'      , ''   , 'integrations_connect_home' )
    INTEGRATIONS_REFERENCE  = ('Content Sources' , ''   , 'integrations_reference_home' )
    INTEGRATIONS_IMPORT     = ('Data Import'     , ''   , 'integrations_import_home' )
    SYSTEM_INFO             = ('System Info'     , ''   , 'system_info' )

    @classmethod
    def default(cls):
        return cls.SETTINGS

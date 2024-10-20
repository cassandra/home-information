from hi.apps.common.enums import LabeledEnum


class ConfigPageType(LabeledEnum):
    # Defines those features that appear on the main config (admin) home
    # page and links to their content.
    
    def __init__( self,
                  label        : str,
                  description  : str,
                  url_name     : str ):
        super().__init__( label, description )
        self.url_name = url_name
        return

    SETTINGS     = ('Settings'     , ''   , 'config_settings' )
    INTEGRATIONS = ('Integrations' , ''   , 'integrations_home' )

    def default(self):
        return ConfigPageType.SETTINGS
    

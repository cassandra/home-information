from dataclasses import dataclass


@dataclass
class IntegrationKey:
    """ Internal identifier to help map to/from an integration's external names/identifiers """

    integration_id    : str  # Internally defined unique identifier for the integration source
    integration_name  : str  # Name or identifier that is used by the external source.

    def __post_init__(self):
        # Want to make matching more robust, so only 
        self.integration_id = self.integration_id.lower()
        self.integration_name = self.integration_name.lower()
        return
    
    def __str__(self):
        return self.integration_key_str

    def __eq__(self, other):
        if isinstance(other, IntegrationKey):
            return self.integration_key_str == other.integration_key_str
        return False

    def __hash__(self):
        return hash(self.integration_key_str)
    
    @property
    def integration_key_str(self):
        return f'{self.integration_id}.{self.integration_name}'

    @classmethod
    def from_string( cls, a_string : str ):
        prefix, suffix = a_string.split( '.', 1 )
        return IntegrationKey(
            integration_id = prefix,
            integration_name = suffix,
        )


    

from hi.apps.common.enums import LabeledEnum


class CollectionType(LabeledEnum):

    """ 
    - This helps define the default visual appearance.
    - No assumptions are made about what sensors or controllers are associated with a given EntityType.
    - SVG file is needed for each of these, else will use a default.
    - SVG filename is by convention:  
    """
    def __init__( self,
                  label           : str,
                  description     : str,
                  is_path         : bool = True,
                  is_path_closed  : bool = True ):
        super().__init__( label, description )
        self.is_path = is_path
        self.is_path_closed = is_path_closed
        return

    APPLIANCES   = ( 'Appliances', '' )
    DEVICES      = ( 'Devices', '' )
    ELECTRONICS  = ( 'Electronics', '' )
    GARDENING    = ( 'Gardening', '' )
    LANDSCAPING  = ( 'Landscaping', '' )
    TOOLS        = ( 'Tools', '' )
    OTHER        = ( 'Other', '' )

    @classmethod
    def default(cls):
        return cls.OTHER

    @property
    def is_icon(self):
        return bool( not self.is_path )

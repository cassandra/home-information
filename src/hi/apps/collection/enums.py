from hi.apps.common.enums import LabeledEnum


class CollectionType(LabeledEnum):

    """ 
    - This helps define the default visual appearance.
    - No assumptions are made about what sensors or controllers are associated with a given EntityType.
    - SVG file is needed for each of these, else will use a default.
    - SVG filename is by convention:  
    """

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

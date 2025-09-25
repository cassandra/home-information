from hi.apps.common.enums import LabeledEnum


class CollectionType(LabeledEnum):

    """ 
    - This helps define the default visual appearance.
    - No assumptions are made about what sensors or controllers are associated with a given EntityType.
    - SVG file is needed for each of these, else will use a default.
    - SVG filename is by convention:  
    """

    APPLIANCES   = ( 'Appliances', '' )
    CAMERAS      = ( 'Cameras', '' )
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
    def is_cameras(self):
        return bool( self == CollectionType.CAMERAS )
    

class CollectionViewType(LabeledEnum):

    GRID   = ( 'Grid', '' )
    LIST   = ( 'List', '' )

    def is_grid(self):
        return self == CollectionViewType.GRID

    def is_list(self):
        return self == CollectionViewType.LIST



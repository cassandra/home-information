from hi.apps.common.enums import LabeledEnum
from hi.apps.common.svg_models import SvgPathStyle, SvgViewBox


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
    
    @property
    def svg_icon_bounding_box(self):
        """
        This defines the bounding box or extents of the SVG drawing commands,
        which we need in order to properly position, rotate and scale the icon.
        We need to be ab le to comute the center, since the adjustable location
        is defining the center point of the icon.
        """
        # TODO: Change this after creating initial icons
        return SvgViewBox( x = 0, y = 0, width = 32, height = 32 )
    
    @property
    def svg_icon_template_name(self):
        """
        A template containing SVG drawing commands for the icon.  It should not
        contain the <svg> tag as this template will be inserted as part of
        the basr location SVG. This file can be one or more SVG drawing
        commands.  A <g> tag will be automatically provided to wrap the
        content os this since that <g> wrapper also need to define the SVG
        transformations needed to properly position, scale and rotate the
        icon. For entities with states, this should also use the "hi-state"
        attribute in order to adjust its appearance (via CSS) based on its 
        state.
        """
        # TODO: Change this after creating initial icons
        #
        #    return f'templates/entity/svg/type.{self.name.lower()}.svg'
        return 'entity/svg/type.other.svg'
    
    @property
    def svg_path_style(self):
        # TODO: Change this to be based on type
        return SvgPathStyle(
            stroke_color = '#40f040',
            stroke_width = 5.0,
            fill_color = 'none',
        )
 

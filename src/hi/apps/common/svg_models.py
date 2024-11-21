from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models


@dataclass
class SvgViewBox:
    x       : float
    y       : float
    width   : float
    height  : float
    
    def __post_init__(self):
        self._max_x = self.x + self.width
        self._max_y = self.y + self.height
        return
        
    def __str__(self):
        return f'{self.x} {self.y} {self.width} {self.height}'
    
    @property
    def min_x(self):
        return self.x
    
    @property
    def min_y(self):
        return self.y
    
    @property
    def max_x(self):
        return self._max_x
    
    @property
    def max_y(self):
        return self._max_y
    
    @staticmethod
    def from_attribute_value( value : str ):
        components = value.split(' ')
        if len(components) != 4:
            raise ValueError( f'Invalid viewBox value "{value}".' )
        return SvgViewBox(
            x = float(components[0]),
            y = float(components[1]),
            width = float(components[2]),
            height = float(components[3]),
        )

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
        }


@dataclass
class SvgIconItem:
    """
    Encapsulates an iten to be inserted in a base SVG file as an icon.  The
    icon is defined as a sequence of drawing commands stored in a template
    file.  The shape that the icon drawing commands define can be
    transformed to scale, roate and change its position as provided.

    The template contains SVG drawing commands for the icon.  It should not
    contain the <svg> tag as this template will be inserted as part of
    the base location SVG. This file can be one or more SVG drawing
    commands.  A <g> tag will be automatically provided to wrap the
    content os this since that <g> wrapper also need to define the SVG
    transformations needed to properly position, scale and rotate the
    icon. For entities with states, this should also use the "hi-state"
    attribute in order to adjust its appearance (via CSS) based on its 
    state.

    The bounding box or extents of the SVG drawing commands, is needed
    in order to properly position, rotate and scale the icon.  We need to
    be able to compute the center, since the adjustable icon location is
    defining the center point of the icon.

    The SVG Transformations needed to move, scale and rotate SVG
    fragments are tricky and inconsistent.
    
      - Scaling changes the coordinate system.
      - Translation does not dirrectly move the item, but insteadmodifies
        the coordinate systems zero point.
      - Scaling has to be accounted for in the translation cooridinates.
      - Translation does not affect the rotate center point.
      - Scaling does not affect the rotate center point
      - Thus, though the transformation order matters, things that
        come before can impact things that come after.
      - Scaling does not always have to be taken into account.
    """
    
    html_id        : str
    template_name  : str
    bounding_box   : SvgViewBox
    position_x     : float
    position_y     : float
    rotate         : float
    scale          : float

    @property
    def transform_str(self):
        return f'scale( {self.scale} ) translate( {self.translate_x} {self.translate_y} ) rotate( {self.rotate} {self.bounds_center_x} {self.bounds_center_y} )'
    
    @property
    def bounds_center_x(self):
        return self.bounding_box.x + ( self.bounding_box.width / 2.0 )

    @property
    def bounds_center_y(self):
        return self.bounding_box.y + ( self.bounding_box.height / 2.0 )

    @property
    def translate_x(self):
        """ Translation needed to put the item's center at the SVG position x. """
        if self.scale < 0.000001:
            return 0
        return ( self.position_x / self.scale ) - self.bounds_center_x

    @property
    def translate_y(self):
        """ Translation needed to put the item's center at the SVG posiiton y. """
        if self.scale < 0.000001:
            return 0
        return ( self.position_y / self.scale ) - self.bounds_center_y


@dataclass
class SvgPathItem:
    """
    Encapsulates an item to be inserted in a base SVG file as a path.  A
    path item is a sequence of drawing commands defined in 'svg_path'.
    """

    html_id       : str
    svg_path      : str
    stroke_color  : str
    stroke_width  : float
    fill_color    : str
    fill_opacity  : float
    

class SvgDecimalField( models.DecimalField ):
    """
    Custom model field for SVG-related decimal values to fix precision and
    round higher precision values.
    """

    def __init__( self, *args, **kwargs ):
        # Set default precision values for SVG fields (can be customized)
        kwargs['max_digits'] = 11
        kwargs['decimal_places'] = 6
        super().__init__( *args, **kwargs )

    def to_python(self, value):
        return self._round_value( value )

    def get_prep_value( self, value ):
        value = super().get_prep_value(value)
        return self._round_value( value )

    def _round_value( self, value ):
        if value is None:
            return value
        try:
            value = Decimal( value )
        except ( TypeError, ValueError ):
            raise ValidationError( f'Invalid decimal value: {value}.')
        
        precision_str = f'1.{"0" * self.decimal_places}'
        precision = Decimal( precision_str )
        return value.quantize( precision, rounding = ROUND_HALF_UP )

    

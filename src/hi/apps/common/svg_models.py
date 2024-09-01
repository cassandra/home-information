from dataclasses import dataclass


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
class SvgPathStyle:
    stroke_color  : str
    stroke_width  : float
    fill_color    : str

    def to_dict(self):
        return {
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'fill_color': self.fill_color,
        }    
    

@dataclass
class SvgItem:
    """
    Encapsulates an iten to be inserted in a base SVG file.  A item is a
    sequence of drawing commands stored in a template.  The shape that the
    drawing commands define can be transformed to scale, roate and chnage
    its position as provided.
    """

    # The SVG Transformations needed to move, scale and rotate SVG
    # fragments are tricky and inconsistent.
    #
    #  - Scaling changes the coordinate system.
    #  - Translation does not dirrectly move the item, but insteadmodifies
    #    the coordinate systems zero point.
    #  - Scaling has to be accounted for in the translation cooridinates.
    #  - Translation does not affect the rotate center point.
    #  - Scaling does not affect the rotate center point
    #  - Thus, though the transformation order matters, things that
    #    come before can impact things that come after.
    #  - Scaling does not always have to be taken into account.
    
    # Template name
    html_id        : str
    template_name  : str
    bounding_box   : SvgViewBox
    position_x     : float
    position_y     : float
    rotate         : float       = 0.0
    scale          : float       = 1.0

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

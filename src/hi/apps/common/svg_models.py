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
    html_id        : str
    template_name  : str
    bounding_box   : SvgViewBox
    position_x     : float
    position_y     : float
    rotate         : float       = 0.0
    scale          : float       = 1.0

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

    @property
    def rotation_x(self):
        if self.scale < 0.000001:
            return 0
        return ( self.position_x / self.scale )

    @property
    def rotation_y(self):
        if self.scale < 0.000001:
            return 0
        return ( self.position_y / self.scale )
    

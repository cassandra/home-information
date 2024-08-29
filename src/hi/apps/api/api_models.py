"""
The models that define the interface and model translations between the
client and server.  This is meant to decouple the client and server data
model spaces. We want the client to be a simple as possible and know as
little as possible about the server's internal models.
"""

from dataclasses import dataclass, field
from typing import List


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
class SvgIconItem:
    """
    A item that is positoned over a base SVG relative to the base SVG
    viewBox.  Styling is defined by CSS classes in the
    icon_filename.  Each itemm will have a "state" HTML attribute that can
    be used to change the appearance of the icon based on state changes and
    sensoir values.  However, those are changes dynamically by the client
    polling for status, so the svg file itself will contain the default
    state value (how it appears when the state is unknown). This structure
    is only used for the initial population of the SVG display when the
    server is first providing the view..
    """
    html_id        : str
    icon_filename  : str
    svg_x          : float
    svg_y          : float
    scale          : float
    rotation       : float

    def to_dict(self):
        return {
            'html_id': self.html_id,
            'icon_filename': self.icon_filename,
            'svg_x': self.svg_x,
            'svg_y': self.svg_y,
            'scale': self.scale,
            'rotation': self.rotation,
        }
    
    
@dataclass
class SvgPathItem:
    html_id         : str
    svg_path        : str  # The value/content of the 'd' attribute
    svg_path_style  : SvgPathStyle
    
    def to_dict(self):
        return {
            'html_id': self.html_id,
            'svg_path': self.svg_path,
            'svg_path_style': self.svg_path_style.to_dict(),
        }

    
@dataclass
class SvgOverlayData:
    """
    All the data the client (Javascript) needs to display items over a a
    base SVG. The positioning is relative to the current view box and
    display area which only the Javascript can know since the dislpay area
    is defined dynamically to be responsive.
    """
    
    base_html_id  : str
    view_box      : SvgViewBox
    rotation      : float
    icon_items    : List[ SvgIconItem ]  = field( default_factory = list )
    path_items    : List[ SvgPathItem ]  = field( default_factory = list )

    def to_dict(self):
        return {
            'html_id': self.html_id,
            'view_box': self.view_box.to_dict(),
            'rotation': self.rotation,
            'icon_items': [ x.to_dict() for x in self.icon_items ],
            'path_items': [ x.to_dict() for x in self.path_items ],
        }
    

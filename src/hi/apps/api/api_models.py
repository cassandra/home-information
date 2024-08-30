"""
The models that define the interface and model translations between the
client and server.  This is meant to decouple the client and server data
model spaces. We want the client to be a simple as possible and know as
little as possible about the server's internal models.
"""

from dataclasses import dataclass, field
import json
from typing import List

from hi.apps.common.svg_models import SvgPathStyle


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
    icon_items    : List[ SvgIconItem ]  = field( default_factory = list )
    path_items    : List[ SvgPathItem ]  = field( default_factory = list )

    def to_dict(self):
        return {
            'base_html_id': self.base_html_id,
            'icon_items': [ x.to_dict() for x in self.icon_items ],
            'path_items': [ x.to_dict() for x in self.path_items ],
        }

    def to_json(self):
        return json.dumps( self.to_dict() )
    

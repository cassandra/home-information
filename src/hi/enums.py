import json
import re
from typing import Dict, List, Tuple

from hi.apps.common.enums import LabeledEnum


class ViewType(LabeledEnum):

    LOCATION_VIEW  = ('Location View', '' )
    COLLECTION     = ('Collection', '' )
    CONFIGURATION  = ('Configuration', '' )
    ENTITY_VIDEO_STREAM  = ('Entity Video Stream', '' )
    SENSOR_VIDEO_BROWSE  = ('Sensor Video Browse', '' )

    @property
    def is_location_view(self):
        return bool( self == ViewType.LOCATION_VIEW )

    @property
    def is_collection(self):
        return bool( self == ViewType.COLLECTION )

    @property
    def is_configuration(self):
        return bool( self == ViewType.CONFIGURATION )

    @property
    def is_video_stream(self):
        return bool( self == ViewType.ENTITY_VIDEO_STREAM )

    @property
    def is_video_browse(self):
        return bool( self == ViewType.SENSOR_VIDEO_BROWSE )

    @property
    def allows_edit_mode(self):
        return bool( self in [ ViewType.LOCATION_VIEW,
                               ViewType.COLLECTION ] )


class ViewMode(LabeledEnum):

    MONITOR      = ('Monitor', '' )
    EDIT         = ('Edit', '' )

    @property
    def is_editing(self):
        return bool( self == ViewMode.EDIT )

    
class ItemType(LabeledEnum):
    # Many class have polymorpic behavior along different dimensions with
    # the dimensions being overlapping between subsets.  This is mostly
    # used on the front-ends Javascript where we try to hide model details
    # and use more a more generic data model for 'items' that could be more
    # than one backend model type.  When the Javascript needs to inform
    # the server of an action, the server needs to be able to map that
    # Javascript concept back to the specifics class.
    
    ENTITY         = ( 'Entity', '' )
    COLLECTION     = ( 'Collection', '' )
    LOCATION       = ( 'Location', '' )
    LOCATION_VIEW  = ( 'Location View', '' )

    @classmethod
    def HTML_ID_ARG(cls):
        return 'html_id'

    @classmethod
    def HTML_ID_LIST_ARG(cls):
        return 'html_id_list'
    
    def html_id( self, item_id : int ):
        return f'hi-{self}-{item_id}'
    
    @classmethod
    def parse_html_id( self, html_id_str : str ) -> Tuple[ 'ItemType', int ]:
        # Prefix is important and an optional suffix must not have digits.
        m = re.match( r'^hi-([\w\-]+)-(\d+)(-\D*|)$', html_id_str )
        if not m:
            raise ValueError( f'Bad html id "{html_id_str}".' )
        return ( ItemType.from_name( m.group(1) ), int(m.group(2)) )
    
    @classmethod
    def parse_from_dict( cls, a_dict : Dict[ str, str ] ) -> Tuple[ 'ItemType', int ]:
        return cls.parse_html_id( a_dict.get( cls.HTML_ID_ARG() ) )
    
    @classmethod
    def parse_list_from_dict( cls, a_dict : Dict[ str, str ] ) -> List[ Tuple[ 'ItemType', int ]  ]:
        html_id_str_list = json.loads( a_dict.get( cls.HTML_ID_LIST_ARG() ) )
        return [ cls.parse_html_id( html_id_str ) for html_id_str in html_id_str_list ]

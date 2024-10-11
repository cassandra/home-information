from hi.apps.common.enums import LabeledEnum


class LocationViewType(LabeledEnum):

    CONTROL      = ('Control', '' )
    INFORMATION  = ('Information', '' )


class SvgItemType(LabeledEnum):

    ICON  = ( 'Icon', '' )
    OPEN_PATH  = ( 'Open Path ', '' )
    CLOSED_PATH  = ( 'Closed Path ', '' )

    @property
    def is_icon(self):
        return bool( self == SvgItemType.ICON )

    @property
    def is_path(self):
        return bool( self in [ SvgItemType.OPEN_PATH, SvgItemType.CLOSED_PATH ] )

    @property
    def is_path_closed(self):
        return bool( self == SvgItemType.CLOSED_PATH )

    

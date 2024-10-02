from hi.apps.common.enums import LabeledEnum


class ViewType(LabeledEnum):

    LOCATION       = ('Location', '' )
    COLLECTION     = ('Collection', '' )

    @property
    def is_location(self):
        return bool( self == ViewType.LOCATION )

    @property
    def is_collection(self):
        return bool( self == ViewType.COLLECTION )


class ViewMode(LabeledEnum):

    MONITOR      = ('Monitor', '' )
    EDIT         = ('Edit', '' )

    @property
    def is_editing(self):
        return bool( self == ViewMode.EDIT )

    @property
    def should_reload_on_view_change(self):
        return bool( self == ViewMode.EDIT )
    

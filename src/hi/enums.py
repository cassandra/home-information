from hi.apps.common.enums import LabeledEnum


class ViewType(LabeledEnum):

    LOCATION_VIEW  = ('Location View', '' )
    COLLECTION     = ('Collection', '' )
    CONFIGURATION  = ('Configuration', '' )

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
    def allows_edit_mode(self):
        return bool( self in [ ViewType.LOCATION_VIEW,
                               ViewType.COLLECTION ] )


class ViewMode(LabeledEnum):

    MONITOR      = ('Monitor', '' )
    EDIT         = ('Edit', '' )

    @property
    def is_editing(self):
        return bool( self == ViewMode.EDIT )

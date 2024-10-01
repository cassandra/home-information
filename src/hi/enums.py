from hi.apps.common.enums import LabeledEnum


class EditMode(LabeledEnum):

    OFF          = ('Off', '' )
    ON           = ('On', '' )

    @property
    def is_editing(self):
        return bool( self != EditMode.OFF )

    @property
    def should_reload_on_location_view_change(self):
        return bool( self != EditMode.OFF )
    

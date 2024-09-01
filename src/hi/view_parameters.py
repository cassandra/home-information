from dataclasses import dataclass

from hi.apps.location.models import LocationView

from .enums import EditMode


@dataclass
class ViewParameters:
    
    location_view_id    : int       = None
    edit_mode           : EditMode  = None
    
    def __post_init__(self):
        if self.edit_mode is None:
            self.edit_mode = EditMode.default()
        self._location_view = None  # Lazy loaded
        return

    @property
    def location_view(self):
        if self._location_view:
            return self._location_view
        if self.location_view_id is None:
            return None
        try:
            self._location_view = LocationView.objects.get( id = self.location_view_id )
            return self._location_view
        except LocationView.DoesNotExist:
            return None
        
    def to_session( self, request ):
        if not hasattr( request, 'session' ):
            return
        request.session['location_view_id'] = self.location_view_id
        request.session['edit_mode'] = str(self.edit_mode)
        return

    @staticmethod
    def from_session( request ):
        if not request:
            return ViewParameters()
        if not hasattr( request, 'session' ):
            return ViewParameters()
        try:
            location_view_id = int( request.session.get( 'location_view_id' ))
        except ( TypeError, ValueError ):
            location_view_id = None

        edit_mode = EditMode.from_name_safe( name = request.session.get( 'edit_mode' ))

        return ViewParameters(
            location_view_id = location_view_id,
            edit_mode = edit_mode,
        )
    

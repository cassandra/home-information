from dataclasses import dataclass

from hi.apps.location.models import LocationView

from .enums import ViewMode


@dataclass
class ViewParameters:
    
    location_view_id    : int       = None
    view_mode           : ViewMode  = None

    def __post_init__(self):
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
        request.session['view_mode'] = str(self.view_mode)
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

        view_mode = ViewMode.from_name_safe( name = request.session.get( 'view_mode' ))

        return ViewParameters(
            location_view_id = location_view_id,
            view_mode = view_mode,
        )
    

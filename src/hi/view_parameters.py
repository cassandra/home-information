from dataclasses import dataclass

from hi.apps.collection.models import Collection
from hi.apps.location.models import LocationView

from .enums import ViewMode, ViewType


@dataclass
class ViewParameters:

    # For anything in this view state that needs to be kept in sync with
    # Javascript, add global variables in the base.html template at start
    # of body and reference in Javascript as needed. e.g., The editing mode
    # requires additional event registrations to handle mouse and gesture
    # events..
    
    view_type         : ViewType  = None
    view_mode         : ViewMode  = None
    location_view_id  : int       = None  # Last LocationView viewed
    collection_id     : int       = None  # Last Collection viewed
    
    def __post_init__(self):
        if self.view_type is None:
            self.view_type = ViewType.default()
        if self.view_mode is None:
            self.view_mode = ViewMode.default()
        self._location = None  # Lazy loaded
        self._location_view = None  # Lazy loaded
        self._collection = None  # Lazy loaded
        return

    @property
    def location(self):
        if self._location:
            return self._location
        location_view = self.location_view
        if not location_view:
            return None
        self._location = location_view.location
        return self._location
    
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
        
    @property
    def collection(self):
        if self._collection:
            return self._collection
        if self.collection_id is None:
            return None
        try:
            self._collection = Collection.objects.get( id = self.collection_id )
            return self._collection
        except Collection.DoesNotExist:
            return None
        
    def to_session( self, request ):
        if not hasattr( request, 'session' ):
            return
        request.session['view_type'] = str(self.view_type)
        request.session['view_mode'] = str(self.view_mode)
        request.session['location_view_id'] = self.location_view_id
        request.session['collection_id'] = self.collection_id
        return

    @staticmethod
    def from_session( request ):
        if not request:
            return ViewParameters()
        if not hasattr( request, 'session' ):
            return ViewParameters()

        view_type = ViewType.from_name_safe( name = request.session.get( 'view_type' ))
        view_mode = ViewMode.from_name_safe( name = request.session.get( 'view_mode' ))

        try:
            location_view_id = int( request.session.get( 'location_view_id' ))
        except ( TypeError, ValueError ):
            location_view_id = None
        try:
            collection_id = int( request.session.get( 'collection_id' ))
        except ( TypeError, ValueError ):
            collection_id = None

        return ViewParameters(
            view_type = view_type,
            view_mode = view_mode,
            location_view_id = location_view_id,
            collection_id = collection_id,
        )
    

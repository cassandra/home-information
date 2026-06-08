from abc import ABC, abstractmethod
from typing import Optional

from django.http import HttpRequest
from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
from hi.apps.entity.entity_placement import EntityPlacer
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import LocationView


class EntityViewMembership( ABC ):
    """The active container (LocationView or Collection) that an entity can
    belong to in the current request.
    """

    @classmethod
    def for_request( cls, request : HttpRequest ) -> Optional[ 'EntityViewMembership' ]:

        view_type = request.view_parameters.view_type
        if view_type.is_location_view:
            location_view = LocationManager().get_default_location_view( request = request )
            return LocationViewEntityMembership( location_view = location_view )
        if view_type.is_collection:
            try:
                collection = CollectionManager().get_default_collection( request = request )
            except Collection.DoesNotExist:
                return None
            return CollectionEntityMembership( collection = collection )
        return None

    def toggle_url( self, entity : Entity ) -> str:
        # Context-agnostic: the toggle view re-resolves the active
        # container from the request, so only the entity id is needed.
        return reverse(
            'edit_entity_view_membership_toggle',
            kwargs = { 'entity_id': entity.id },
        )

    @abstractmethod
    def is_member( self, entity : Entity ) -> bool:
        ...

    @abstractmethod
    def toggle( self, entity : Entity ) -> bool:
        """Add the entity to / remove it from the active container,
        returning the new membership state."""
        ...

    @property
    @abstractmethod
    def target_label( self ) -> str:
        """Human label for the container, e.g. ``'View'`` / ``'Collection'``."""
        ...


class LocationViewEntityMembership( EntityViewMembership ):

    def __init__( self, location_view : LocationView ):
        self._location_view = location_view

    def is_member( self, entity : Entity ) -> bool:
        return self._location_view.entity_views.filter( entity = entity ).exists()

    def toggle( self, entity : Entity ) -> bool:
        return EntityPlacer().toggle_entity_in_view(
            entity = entity,
            location_view = self._location_view,
        )

    @property
    def target_label( self ) -> str:
        return 'View'


class CollectionEntityMembership( EntityViewMembership ):

    def __init__( self, collection : Collection ):
        self._collection = collection

    def is_member( self, entity : Entity ) -> bool:
        return self._collection.entities.filter( entity = entity ).exists()

    def toggle( self, entity : Entity ) -> bool:
        return CollectionManager().toggle_entity_in_collection(
            entity = entity,
            collection = self._collection,
        )

    @property
    def target_label( self ) -> str:
        return 'Collection'

import logging
from types import SimpleNamespace

from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.collection.models import Collection
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewType
from hi.testing.base_test_case import BaseTestCase

from hi.apps.edit.entity_membership import (
    EntityViewMembership,
    LocationViewEntityMembership,
    CollectionEntityMembership,
)

logging.disable(logging.CRITICAL)


class TestEntityViewMembership(BaseTestCase):
    """The edit-app bridge that toggles an entity's membership in the
    active LocationView / Collection. Verifies the factory branch by view
    type and the membership round-trip (geometry is per-Location, so the
    toggle is pure membership)."""

    def test_for_request_returns_none_for_non_membership_view_type(self):
        # Configuration / video views have no entity-membership concept, so
        # no add/remove control should be offered.
        request = SimpleNamespace(
            view_parameters = SimpleNamespace( view_type = ViewType.CONFIGURATION ),
        )
        self.assertIsNone( EntityViewMembership.for_request( request ) )

    def test_location_view_membership_toggle_round_trip(self):
        location = Location.objects.create(
            name = 'L',
            svg_fragment_filename = 'l.svg',
            svg_view_box_str = '0 0 100 100',
        )
        location_view = LocationView.objects.create(
            location = location,
            name = 'V',
            location_view_type_str = 'MAIN',
            svg_view_box_str = '0 0 100 100',
            svg_rotate = 0.0,
        )
        entity = Entity.objects.create(
            name = 'E', entity_type_str = str(EntityType.LIGHT),
        )
        membership = LocationViewEntityMembership( location_view = location_view )

        self.assertEqual( membership.target_label, 'View' )
        self.assertFalse( membership.is_member( entity ) )
        self.assertTrue( membership.toggle( entity ) )       # added
        self.assertTrue( membership.is_member( entity ) )
        self.assertFalse( membership.toggle( entity ) )      # removed
        self.assertFalse( membership.is_member( entity ) )

    def test_collection_membership_toggle_round_trip(self):
        collection = Collection.objects.create(
            name = 'C',
            collection_type_str = str(CollectionType.OTHER),
            collection_view_type_str = str(CollectionViewType.GRID),
        )
        entity = Entity.objects.create(
            name = 'E2', entity_type_str = str(EntityType.LIGHT),
        )
        membership = CollectionEntityMembership( collection = collection )

        self.assertEqual( membership.target_label, 'Collection' )
        self.assertFalse( membership.is_member( entity ) )
        self.assertTrue( membership.toggle( entity ) )       # added
        self.assertTrue( membership.is_member( entity ) )
        self.assertFalse( membership.toggle( entity ) )      # removed
        self.assertFalse( membership.is_member( entity ) )

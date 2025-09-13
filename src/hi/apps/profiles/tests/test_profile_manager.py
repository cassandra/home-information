import logging
from pathlib import Path

from hi.apps.profiles.profile_manager import ProfileManager
from hi.apps.profiles.enums import ProfileType
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.location.models import Location, LocationView
from hi.apps.collection.models import Collection, CollectionEntity
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestProfileManager(BaseTestCase):
    """Unit tests for ProfileManager that iterate through all ProfileType enum values."""

    def setUp(self):
        super().setUp()
        self.profile_manager = ProfileManager()

    def _test_profile_loading(self, profile_type: ProfileType):
        """
        Helper method to test profile loading for a given ProfileType.
        
        Tests that ProfileManager can:
        1. Load the actual JSON data from the data directory
        2. Create database objects successfully
        3. Verify key objects are present in the database
        """
        # Verify JSON file exists
        json_path = self.profile_manager._get_profile_json_path(profile_type)
        self.assertTrue(Path(json_path).exists(), f"JSON file should exist at {json_path}")
        
        # Load the profile - should not raise any exceptions
        try:
            self.profile_manager.load_profile(profile_type)
        except Exception as e:
            self.fail(f"Profile loading should succeed but raised: {e}")
        
        # Verify database objects were created
        location_count = Location.objects.count()
        entity_count = Entity.objects.count()
        collection_count = Collection.objects.count()
        
        # All profiles should create at least some objects
        self.assertGreater(location_count, 0, "Profile should create at least one location")
        self.assertGreater(entity_count, 0, "Profile should create at least one entity")
        
        # Verify related objects were created
        entity_position_count = EntityPosition.objects.count()
        location_view_count = LocationView.objects.count()
        
        self.assertGreater(entity_position_count, 0, "Profile should create entity positions")
        self.assertGreater(location_view_count, 0, "Profile should create location views")
        
        # Verify entities have required fields
        first_entity = Entity.objects.first()
        self.assertIsNotNone(first_entity.name, "Entity should have a name")
        self.assertIsNotNone(first_entity.entity_type_str, "Entity should have entity_type_str")
        # Verify enum values are stored as lowercase
        self.assertEqual(first_entity.entity_type_str, first_entity.entity_type_str.lower(), 
                         "Entity type should be stored as lowercase")
        
        # Verify locations have required fields
        first_location = Location.objects.first()
        self.assertIsNotNone(first_location.name, "Location should have a name")
        self.assertIsNotNone(first_location.svg_fragment_filename,
                             "Location should have svg_fragment_filename")
        
        # Verify location views have lowercase enum values
        if location_view_count > 0:
            first_location_view = LocationView.objects.first()
            self.assertEqual(first_location_view.location_view_type_str, 
                             first_location_view.location_view_type_str.lower(),
                             "LocationView type should be stored as lowercase")
            self.assertEqual(first_location_view.svg_style_name_str,
                             first_location_view.svg_style_name_str.lower(),
                             "SVG style name should be stored as lowercase")
        
        # If collections exist, verify they are properly configured
        if collection_count > 0:
            first_collection = Collection.objects.first()
            self.assertIsNotNone(first_collection.name, "Collection should have a name")
            self.assertIsNotNone(first_collection.collection_type_str,
                                 "Collection should have collection_type_str")
            # Verify collection enum values are lowercase
            self.assertEqual(first_collection.collection_type_str,
                             first_collection.collection_type_str.lower(),
                             "Collection type should be stored as lowercase")
            self.assertEqual(first_collection.collection_view_type_str,
                             first_collection.collection_view_type_str.lower(),
                             "Collection view type should be stored as lowercase")
            
            # Check for collection-entity relationships
            collection_entity_count = CollectionEntity.objects.count()
            if collection_entity_count > 0:
                self.assertGreater(collection_entity_count, 0, "Collections should have entity relationships")

    def test_single_story_profile_loading(self):
        """Test loading SINGLE_STORY profile from actual JSON data."""
        self._test_profile_loading(ProfileType.SINGLE_STORY)

    def test_two_story_profile_loading(self):
        """Test loading TWO_STORY profile from actual JSON data."""
        self._test_profile_loading(ProfileType.TWO_STORY)

    def test_apartment_profile_loading(self):
        """Test loading APARTMENT profile from actual JSON data."""
        self._test_profile_loading(ProfileType.APARTMENT)

    def test_profile_requires_empty_database(self):
        """Test that profile loading fails when database is not empty."""
        # Create an entity to make database non-empty
        Entity.objects.create(name='Existing Entity', entity_type_str='light')
        
        # Try to load a profile - should raise ValueError
        with self.assertRaises(ValueError):
            self.profile_manager.load_profile(ProfileType.SINGLE_STORY)
        return
    
    def test_profile_json_filename_generation(self):
        """Test that ProfileType enum generates correct JSON filenames."""
        for profile_type in ProfileType:
            filename = profile_type.json_filename()
            expected_pattern = f"profile_{profile_type}.json"
            self.assertEqual(filename, expected_pattern, 
                             f"JSON filename should match pattern for {profile_type}")
            
            # Verify the actual file exists
            json_path = self.profile_manager._get_profile_json_path(profile_type)
            self.assertTrue(Path(json_path).exists(), 
                            f"JSON file should exist for {profile_type} at {json_path}")

    def test_all_profile_types_have_valid_json_data(self):
        """Test that all ProfileType enum values have valid, loadable JSON data."""
        for profile_type in ProfileType:
            json_path = self.profile_manager._get_profile_json_path(profile_type)
            
            # Should be able to load JSON without errors
            try:
                profile_data = self.profile_manager._load_json_file(json_path)
                self.assertIsInstance(profile_data, dict, 
                                      f"Profile data should be a dictionary for {profile_type}")
                
                # Verify basic structure exists
                self.assertIn('locations', profile_data, 
                              f"Profile should have 'locations' key for {profile_type}")
                self.assertIn('entities', profile_data, 
                              f"Profile should have 'entities' key for {profile_type}")
                
            except Exception as e:
                self.fail(f"Failed to load JSON for {profile_type}: {e}")

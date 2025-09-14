import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

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
            stats = self.profile_manager.load_profile(profile_type)
        except Exception as e:
            self.fail(f"Profile loading should succeed but raised: {e}")
        
        # Verify perfect loading stats - real JSON files should have zero failures
        self.assertTrue(stats.meets_minimum_requirements(), 
                        f"Perfect JSON files should meet minimum requirements for {profile_type}")
        self.assertEqual(stats.locations_failed, 0, 
                         f"Perfect JSON should have zero location failures for {profile_type}")
        self.assertEqual(stats.entities_failed, 0, 
                         f"Perfect JSON should have zero entity failures for {profile_type}")
        self.assertEqual(stats.collections_failed, 0, 
                         f"Perfect JSON should have zero collection failures for {profile_type}")
        self.assertEqual(stats.location_views_failed, 0, 
                         f"Perfect JSON should have zero location view failures for {profile_type}")
        self.assertEqual(stats.entity_positions_failed, 0, 
                         f"Perfect JSON should have zero entity position failures for {profile_type}")
        self.assertEqual(stats.entity_paths_failed, 0, 
                         f"Perfect JSON should have zero entity path failures for {profile_type}")
        self.assertEqual(stats.entity_views_failed, 0, 
                         f"Perfect JSON should have zero entity view failures for {profile_type}")
        self.assertEqual(stats.collection_entities_failed, 0, 
                         f"Perfect JSON should have zero collection entity failures for {profile_type}")
        self.assertEqual(stats.collection_positions_failed, 0, 
                         f"Perfect JSON should have zero collection position failures for {profile_type}")
        self.assertEqual(stats.collection_paths_failed, 0, 
                         f"Perfect JSON should have zero collection path failures for {profile_type}")
        self.assertEqual(stats.collection_views_failed, 0, 
                         f"Perfect JSON should have zero collection view failures for {profile_type}")
        
        # Verify attempted counts equal successful counts (since failures are zero)
        self.assertEqual(stats.locations_attempted, stats.locations_succeeded,
                         f"Perfect JSON: locations attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.entities_attempted, stats.entities_succeeded,
                         f"Perfect JSON: entities attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.collections_attempted, stats.collections_succeeded,
                         f"Perfect JSON: collections attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.location_views_attempted, stats.location_views_succeeded,
                         f"Perfect JSON: location views attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.entity_positions_attempted, stats.entity_positions_succeeded,
                         f"Perfect JSON: entity positions attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.entity_paths_attempted, stats.entity_paths_succeeded,
                         f"Perfect JSON: entity paths attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.entity_views_attempted, stats.entity_views_succeeded,
                         f"Perfect JSON: entity views attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.collection_entities_attempted, stats.collection_entities_succeeded,
                         f"Perfect JSON: collection entities attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.collection_positions_attempted, stats.collection_positions_succeeded,
                         f"Perfect JSON: collection positions attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.collection_paths_attempted, stats.collection_paths_succeeded,
                         f"Perfect JSON: collection paths attempted should equal succeeded for {profile_type}")
        self.assertEqual(stats.collection_views_attempted, stats.collection_views_succeeded,
                         f"Perfect JSON: collection views attempted should equal succeeded for {profile_type}")
        
        # Verify success counts match database counts
        self.assertEqual(stats.locations_succeeded, Location.objects.count(), 
                         f"Location success count should match database count for {profile_type}")
        self.assertEqual(stats.entities_succeeded, Entity.objects.count(), 
                         f"Entity success count should match database count for {profile_type}")
        self.assertEqual(stats.collections_succeeded, Collection.objects.count(), 
                         f"Collection success count should match database count for {profile_type}")
        
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
        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                self._test_profile_loading(ProfileType.SINGLE_STORY)

    def test_two_story_profile_loading(self):
        """Test loading TWO_STORY profile from actual JSON data."""
        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                self._test_profile_loading(ProfileType.TWO_STORY)

    def test_apartment_profile_loading(self):
        """Test loading APARTMENT profile from actual JSON data."""
        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
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
            expected_pattern = f"assets/profiles/{profile_type}.json"
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

    def test_svg_fragment_file_management_with_test_isolation(self):
        """Test SVG fragment copying with proper test isolation using temporary directories."""
        import os
        
        # Create temporary directories for test isolation
        with tempfile.TemporaryDirectory() as temp_media_root:
            with tempfile.TemporaryDirectory() as temp_assets_root:
                # Set up test assets directory structure
                test_assets_dir = Path(temp_assets_root)
                test_svg_dir = test_assets_dir / 'location' / 'svg'
                test_svg_dir.mkdir(parents=True, exist_ok=True)
                
                # Create test SVG fragment files
                test_svg_files = {
                    'location/svg/single_story-0.svg': '<g id="test-main">Test Main Floor</g>',
                    'location/svg/single_story-1.svg': '<g id="test-main">Test Main Floor</g>',
                }
                
                for svg_path, svg_content in test_svg_files.items():
                    full_svg_path = test_assets_dir / svg_path
                    with open(full_svg_path, 'w') as f:
                        f.write(svg_content)
                
                # Use Django's override_settings and patch the assets directory
                with self.settings(MEDIA_ROOT=temp_media_root):
                    with patch.object(self.profile_manager,
                                      '_get_assets_base_directory',
                                      return_value=test_assets_dir):
                        
                        # Test the actual profile loading with SVG copying
                        stats = self.profile_manager.load_profile(ProfileType.SINGLE_STORY)
                        self.assertTrue(stats.meets_minimum_requirements())
                        
                        # Verify that SVG files were copied to test MEDIA_ROOT
                        for svg_filename in test_svg_files.keys():
                            media_path = os.path.join(temp_media_root, svg_filename)
                            self.assertTrue(
                                os.path.exists(media_path), 
                                f"SVG file should be copied to test MEDIA_ROOT: {media_path}")
                            
                            # Verify file content was copied correctly
                            with open(media_path, 'r') as f:
                                copied_content = f.read()
                            self.assertEqual(
                                copied_content, test_svg_files[svg_filename],
                                f"SVG file content should match: {svg_filename}")
                        
                        # Verify database objects were created
                        locations = Location.objects.all()
                        self.assertGreater(locations.count(), 0, "Should create locations")
                        
                        for location in locations:
                            self.assertIsNotNone(
                                location.svg_fragment_filename,
                                "Location should have SVG fragment filename")
                            # Verify the referenced file exists in test MEDIA_ROOT
                            full_path = os.path.join(temp_media_root, location.svg_fragment_filename)
                            self.assertTrue(
                                os.path.exists(full_path),
                                f"Location SVG file should exist in test MEDIA_ROOT: {full_path}")
    
    def test_real_profile_assets_exist(self):
        """Test that the real profile JSON files point to existing assets."""
        for profile_type in ProfileType:
            # Load the real JSON file
            json_path = self.profile_manager._get_profile_json_path(profile_type)
            profile_data = self.profile_manager._load_json_file(json_path)
            
            # Check that all referenced SVG files exist in the real assets directory
            locations_data = profile_data.get('locations', [])
            assets_base_dir = self.profile_manager._get_assets_base_directory()
            
            for location_data in locations_data:
                svg_filename = location_data.get('svg_fragment_filename')
                if svg_filename:
                    asset_path = assets_base_dir / svg_filename
                    self.assertTrue(
                        asset_path.exists(), 
                        f"Real profile {profile_type} references missing asset: {asset_path}")
    
    def test_profile_svg_copying_error_handling(self):
        """Test error handling when SVG fragment files are missing from assets."""
        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                # Mock a missing SVG file by patching the copy method
                with patch.object(self.profile_manager, '_copy_svg_fragment_files') as mock_copy:
                    # Make the copy method raise FileNotFoundError
                    mock_copy.side_effect = FileNotFoundError("SVG fragment file not found in assets")
                    
                    # Should raise FileNotFoundError when SVG file is missing
                    with self.assertRaises(FileNotFoundError):
                        self.profile_manager.load_profile(ProfileType.SINGLE_STORY)

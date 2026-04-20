import logging
import tempfile
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

    def test_svg_template_rendering_to_media(self):
        """Test that profile loading renders SVG templates to MEDIA_ROOT files."""
        import os

        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                stats = self.profile_manager.load_profile(ProfileType.SINGLE_STORY)
                self.assertTrue(stats.meets_minimum_requirements())

                locations = Location.objects.all()
                self.assertGreater(locations.count(), 0, "Should create locations")

                for location in locations:
                    self.assertIsNotNone(
                        location.svg_fragment_filename,
                        "Location should have SVG fragment filename")
                    full_path = os.path.join(temp_media_root, location.svg_fragment_filename)
                    self.assertTrue(
                        os.path.exists(full_path),
                        f"Rendered SVG should exist in MEDIA_ROOT: {full_path}")
                    # Verify file has content
                    with open(full_path, 'r') as f:
                        content = f.read()
                    self.assertGreater(len(content), 0,
                                       f"SVG file should not be empty: {full_path}")
    
    def test_real_profile_templates_exist(self):
        """Test that the real profile JSON files reference existing SVG templates."""
        from django.template.loader import get_template

        for profile_type in ProfileType:
            json_path = self.profile_manager._get_profile_json_path(profile_type)
            profile_data = self.profile_manager._load_json_file(json_path)

            for location_data in profile_data.get('locations', []):
                svg_template_name = location_data.get('svg_template_name')
                if svg_template_name:
                    try:
                        get_template(svg_template_name)
                    except Exception:
                        self.fail(
                            f"Profile {profile_type} references missing template: {svg_template_name}"
                        )
    
    def test_profile_svg_template_error_handling(self):
        """Test error handling when SVG template references are invalid."""
        with tempfile.TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                # Load real profile data and corrupt the template reference
                json_path = self.profile_manager._get_profile_json_path(ProfileType.SINGLE_STORY)
                profile_data = self.profile_manager._load_json_file(json_path)
                profile_data['locations'][0]['svg_template_name'] = 'profiles/svg/backgrounds/nonexistent.svg'

                with self.assertRaises(Exception):
                    self.profile_manager._render_svg_templates(profile_data)

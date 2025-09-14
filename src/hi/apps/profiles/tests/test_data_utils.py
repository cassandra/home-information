import json
from pathlib import Path
from typing import Dict, Any

from hi.apps.profiles.enums import ProfileType
from hi.apps.profiles.profile_manager import ProfileManager


class ProfileTestDataGenerator:
    """Utility class for generating malformed profile data for error testing."""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
    
    def load_base_profile_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Load a real profile JSON file as base data for modifications."""
        json_path = self.profile_manager._get_profile_json_path(profile_type)
        return self.profile_manager._load_json_file(json_path)
    
    def create_missing_svg_file_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with non-existent SVG file references."""
        data = self.load_base_profile_data(profile_type)
        
        # Corrupt first location's SVG file reference
        if data.get('locations') and len(data['locations']) > 0:
            data['locations'][0]['svg_fragment_filename'] = 'location/svg/nonexistent-file.svg'
        
        return data
    
    def create_invalid_entity_types_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with invalid entity type strings."""
        data = self.load_base_profile_data(profile_type)
        
        # Corrupt first entity's type
        if data.get('entities') and len(data['entities']) > 0:
            data['entities'][0]['entity_type_str'] = 'INVALID_ENTITY_TYPE'
        
        return data
    
    def create_invalid_location_view_types_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with invalid location view type strings."""
        data = self.load_base_profile_data(profile_type)
        
        # Corrupt first location view's type
        if (data.get('locations') and len(data['locations']) > 0
                and data['locations'][0].get('views') and len(data['locations'][0]['views']) > 0):
            data['locations'][0]['views'][0]['location_view_type_str'] = 'INVALID_VIEW_TYPE'
        
        return data
    
    def create_missing_required_fields_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with missing required fields."""
        data = self.load_base_profile_data(profile_type)
        
        # Remove required field from first entity
        if data.get('entities') and len(data['entities']) > 0:
            if 'name' in data['entities'][0]:
                del data['entities'][0]['name']
        
        return data
    
    def create_invalid_foreign_key_references_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with invalid location references in entity positions."""
        data = self.load_base_profile_data(profile_type)
        
        # Create invalid location reference in entity position
        if data.get('entities') and len(data['entities']) > 0:
            for entity in data['entities']:
                if entity.get('positions') and len(entity['positions']) > 0:
                    entity['positions'][0]['location_name'] = 'NonexistentLocation'
                    break
        
        return data
    
    def create_all_locations_invalid_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data where all locations will fail to load (for minimum viability testing)."""
        data = self.load_base_profile_data(profile_type)
        
        # Make all locations reference non-existent SVG files
        for location in data.get('locations', []):
            location['svg_fragment_filename'] = f'location/svg/invalid-{location.get("name", "unknown")}.svg'
        
        return data
    
    def create_all_entities_invalid_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data where all entities will fail to load (for minimum viability testing)."""
        data = self.load_base_profile_data(profile_type)
        
        # Make all entities have invalid types
        for i, entity in enumerate(data.get('entities', [])):
            entity['entity_type_str'] = f'INVALID_TYPE_{i}'
        
        return data
    
    def create_mixed_valid_invalid_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with mix of valid and invalid items (should meet minimum requirements)."""
        data = self.load_base_profile_data(profile_type)
        
        # Corrupt some but not all locations (ensure at least 1 remains valid)
        locations = data.get('locations', [])
        if len(locations) > 1:
            locations[0]['svg_fragment_filename'] = 'location/svg/invalid-first.svg'  # Make first invalid
            # Leave others valid
        
        # Corrupt some but not all entities (ensure at least 1 remains valid)
        entities = data.get('entities', [])
        if len(entities) > 1:
            entities[0]['entity_type_str'] = 'INVALID_FIRST_ENTITY'  # Make first invalid
            # Leave others valid
        
        return data
    
    def create_no_locations_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with no locations (should fail fundamental validation)."""
        data = self.load_base_profile_data(profile_type)
        data['locations'] = []
        return data
    
    def create_no_entities_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with no entities (should fail fundamental validation)."""
        data = self.load_base_profile_data(profile_type)
        data['entities'] = []
        return data
    
    def create_invalid_collection_types_data(self, profile_type: ProfileType = ProfileType.SINGLE_STORY) -> Dict[str, Any]:
        """Create profile data with invalid collection type strings."""
        data = self.load_base_profile_data(profile_type)
        
        # Corrupt first collection's type if collections exist
        if data.get('collections') and len(data['collections']) > 0:
            data['collections'][0]['collection_type_str'] = 'INVALID_COLLECTION_TYPE'
        
        return data
    
    def save_test_data_to_temp_file(self, data: Dict[str, Any], filename: str) -> Path:
        """Save test data to a temporary file and return the path."""
        temp_dir = Path('/tmp')
        temp_file = temp_dir / filename
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return temp_file

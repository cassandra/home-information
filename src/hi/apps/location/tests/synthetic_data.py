"""
Synthetic data generators for Location and LocationView testing.

Provides centralized, reusable test data creation following the project's
synthetic data pattern documented in test-data-management.md.
"""
import uuid
from typing import Optional, Dict, Any, List
from django.core.files.uploadedfile import SimpleUploadedFile

from hi.constants import DIVID
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.location.models import Location, LocationView, LocationAttribute
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.entity.enums import EntityType
from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.location.enums import LocationViewType


class LocationSyntheticData:
    """Centralized synthetic data generators for location testing."""
    
    @staticmethod
    def create_test_location(**kwargs) -> Location:
        """Create a test location with reasonable defaults."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Location {unique_id}',
            'svg_fragment_filename': f'test-location-{unique_id}.svg',
            'svg_view_box_str': '0 0 800 600',
        }
        defaults.update(kwargs)
        return Location.objects.create(**defaults)
    
    @staticmethod
    def create_test_location_view(location: Optional[Location] = None, **kwargs) -> LocationView:
        """Create a test location view with reasonable defaults."""
        if location is None:
            location = LocationSyntheticData.create_test_location()
        
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'location': location,
            'name': f'Test View {unique_id}',
            'location_view_type_str': str(LocationViewType.DEFAULT),
            'svg_view_box_str': '0 0 800 600',
            'order_id': 0,
            'svg_rotate': 0.0,
        }
        defaults.update(kwargs)
        return LocationView.objects.create(**defaults)
    
    @staticmethod
    def create_test_entity_with_position(location: Optional[Location] = None, **kwargs) -> Entity:
        """Create a test entity with position on a location."""
        if location is None:
            location = LocationSyntheticData.create_test_location()
            
        unique_id = str(uuid.uuid4())[:8]
        entity_defaults = {
            'name': f'Test Entity {unique_id}',
            'integration_id': f'test.entity.{unique_id}',
            'integration_name': 'test_integration',
            'entity_type_str': str(EntityType.LIGHT),
        }
        # Extract position-specific kwargs
        position_kwargs = {
            'svg_x': kwargs.pop('svg_x', 100.0),
            'svg_y': kwargs.pop('svg_y', 100.0),
            'svg_rotate': kwargs.pop('svg_rotate', 0.0),
            'svg_scale': kwargs.pop('svg_scale', 1.0),
        }
        entity_defaults.update(kwargs)
        entity = Entity.objects.create(**entity_defaults)
        
        # Create position
        EntityPosition.objects.create(
            entity=entity,
            location=location,
            **position_kwargs
        )
        return entity
    
    @staticmethod
    def create_test_collection_with_position(location: Optional[Location] = None, **kwargs) -> Collection:
        """Create a test collection with position on a location."""
        if location is None:
            location = LocationSyntheticData.create_test_location()
            
        unique_id = str(uuid.uuid4())[:8]
        collection_defaults = {
            'name': f'Test Collection {unique_id}',
            'collection_type_str': str(CollectionType.OTHER),
            'collection_view_type_str': str(CollectionViewType.LIST),
        }
        # Extract position-specific kwargs
        position_kwargs = {
            'svg_x': kwargs.pop('svg_x', 200.0),
            'svg_y': kwargs.pop('svg_y', 200.0), 
            'svg_rotate': kwargs.pop('svg_rotate', 0.0),
            'svg_scale': kwargs.pop('svg_scale', 1.0),
        }
        collection_defaults.update(kwargs)
        collection = Collection.objects.create(**collection_defaults)
        
        # Create position
        CollectionPosition.objects.create(
            collection=collection,
            location=location,
            **position_kwargs
        )
        return collection


class LocationAttributeSyntheticData:
    """Centralized synthetic data generators for location attribute testing."""
    
    @staticmethod
    def create_test_location(**kwargs) -> Location:
        """Create a test location with reasonable defaults."""
        # Generate unique name to avoid constraint violations
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Location {unique_id}',
            'svg_fragment_filename': f'test-location-{unique_id}.svg',
            'svg_view_box_str': '0 0 800 600'
        }
        defaults.update(kwargs)
        return Location.objects.create(**defaults)
    
    @staticmethod
    def create_test_text_attribute(location: Optional[Location] = None, **kwargs) -> LocationAttribute:
        """Create a text attribute with reasonable defaults."""
        if location is None:
            location = LocationAttributeSyntheticData.create_test_location()
            
        defaults = {
            'location': location,
            'name': 'test_property',
            'value': 'test value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_test_file_attribute(location: Optional[Location] = None, **kwargs) -> LocationAttribute:
        """Create a file attribute with reasonable defaults."""
        if location is None:
            location = LocationAttributeSyntheticData.create_test_location()
        
        # Create test file if not provided
        if 'file_value' not in kwargs:
            test_file = SimpleUploadedFile(
                "test_document.txt",
                b"test file content for synthetic data",
                content_type="text/plain"
            )
            kwargs['file_value'] = test_file
            
        defaults = {
            'location': location,
            'name': 'test_document',
            'value': 'Test Document Title',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.FILE),
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_test_secret_attribute(location: Optional[Location] = None, **kwargs) -> LocationAttribute:
        """Create a secret attribute with reasonable defaults."""
        if location is None:
            location = LocationAttributeSyntheticData.create_test_location()
            
        defaults = {
            'location': location,
            'name': 'api_key',
            'value': 'secret_api_key_12345',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.SECRET),
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_location_with_mixed_attributes(**location_kwargs) -> Location:
        """Create a location with a variety of attribute types for comprehensive testing."""
        location = LocationAttributeSyntheticData.create_test_location(**location_kwargs)
        
        # Create various attribute types
        LocationAttributeSyntheticData.create_test_text_attribute(
            location=location, name='description', value='Test location for mixed testing'
        )
        LocationAttributeSyntheticData.create_test_secret_attribute(
            location=location, name='access_code', value='super_secret_code'
        )
        LocationAttributeSyntheticData.create_test_file_attribute(
            location=location, name='floor_plan', value='Floor Plan Document'
        )
        
        return location
    
    @staticmethod
    def create_test_image_file() -> SimpleUploadedFile:
        """Create a test image file for file upload testing."""
        return SimpleUploadedFile(
            "test_image.jpg",
            b"fake jpeg image content for testing",
            content_type="image/jpeg"
        )
    
    @staticmethod
    def create_test_pdf_file() -> SimpleUploadedFile:
        """Create a test PDF file for file upload testing."""
        return SimpleUploadedFile(
            "test_document.pdf",
            b"fake pdf content for testing",
            content_type="application/pdf"
        )
    
    @staticmethod
    def create_large_text_file() -> SimpleUploadedFile:
        """Create a large text file for file size testing."""
        large_content = "Large file content line.\n" * 1000
        return SimpleUploadedFile(
            "large_file.txt",
            large_content.encode(),
            content_type="text/plain"
        )
    
    @staticmethod
    def create_form_data_for_location_edit(location: Location, **overrides) -> Dict[str, Any]:
        """Create complete form data dictionary for location editing form submissions.
        
        Includes both location form data and formset data for regular attributes.
        """
        # Location form data
        form_data = {
            'name': location.name,
            'svg_fragment_filename': location.svg_fragment_filename,
            'svg_view_box_str': location.svg_view_box_str,
        }
        form_data.update(overrides)
        
        # Add formset data for regular attributes (non-file attributes)
        regular_attributes = list(location.attributes.exclude(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id'))
        
        # Use LocationEditFormHandler as the single source of truth for prefix logic
        prefix = f'location-{location.id}'
        
        # Formset management form data
        formset_data = {
            f'{prefix}-TOTAL_FORMS': str(len(regular_attributes) + 1),  # +1 for empty form
            f'{prefix}-INITIAL_FORMS': str(len(regular_attributes)),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }
        
        # Individual attribute form data
        for i, attr in enumerate(regular_attributes):
            formset_data.update({
                f'{prefix}-{i}-id': str(attr.id),
                f'{prefix}-{i}-name': attr.name,
                f'{prefix}-{i}-value': attr.value,
                f'{prefix}-{i}-attribute_type_str': attr.attribute_type_str,
            })
        
        form_data.update(formset_data)
        return form_data
    
    @staticmethod
    def create_formset_data_for_attributes(attributes: List[LocationAttribute], location: Location) -> Dict[str, Any]:
        """Create formset data dictionary for attribute formset submissions."""
        prefix = f'location-{location.id}'
        data = {
            f'{prefix}-TOTAL_FORMS': str(len(attributes) + 1),  # +1 for empty form
            f'{prefix}-INITIAL_FORMS': str(len(attributes)),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }
        
        for i, attr in enumerate(attributes):
            data.update({
                f'{prefix}-{i}-id': str(attr.id),
                f'{prefix}-{i}-name': attr.name,
                f'{prefix}-{i}-value': attr.value,
                f'{prefix}-{i}-attribute_type_str': attr.attribute_type_str,
            })
        
        return data
    
    @staticmethod
    def create_file_title_update_data(location: Location, file_attributes: List[LocationAttribute]) -> Dict[str, str]:
        """Create POST data for file title updates."""
        data = {}
        for attr in file_attributes:
            field_name = f'file_title_{location.id}_{attr.id}'
            data[field_name] = f'Updated {attr.name}'
        return data
    
    @staticmethod
    def create_file_deletion_data(file_attributes: List[LocationAttribute]) -> Dict[str, List[str]]:
        """Create POST data for file deletions."""
        return {
            DIVID['ATTR_V2_DELETE_FILE_ATTR']: [str(attr.id) for attr in file_attributes]
        }

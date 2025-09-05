"""
Synthetic data generators for Entity and EntityAttribute testing.

Provides centralized, reusable test data creation following the project's
synthetic data pattern documented in test-data-management.md.
"""
import uuid
from django.core.files.uploadedfile import SimpleUploadedFile
from typing import Optional, Dict, Any, List

from hi.constants import DIVID
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.entity.enums import EntityType
from hi.apps.location.models import Location


class EntityAttributeSyntheticData:
    """Centralized synthetic data generators for entity attribute testing."""
    
    @staticmethod
    def create_test_location(**kwargs) -> Location:
        """Create a test location with reasonable defaults."""
        defaults = {
            'name': 'Test Location',
            'svg_fragment_filename': 'test-location.svg',
            'svg_view_box_str': '0 0 800 600'
        }
        defaults.update(kwargs)
        return Location.objects.create(**defaults)
    
    @staticmethod
    def create_test_entity(**kwargs) -> Entity:
        """Create a test entity with reasonable defaults."""
        # Generate unique integration_id to avoid constraint violations
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': 'Test Entity',
            'integration_id': f'test.entity.{unique_id}',
            'integration_name': 'test_integration',
            'entity_type_str': str(EntityType.LIGHT),
        }
        defaults.update(kwargs)
        return Entity.objects.create(**defaults)
    
    @staticmethod
    def create_test_text_attribute(entity: Optional[Entity] = None, **kwargs) -> EntityAttribute:
        """Create a text attribute with reasonable defaults."""
        if entity is None:
            entity = EntityAttributeSyntheticData.create_test_entity()
            
        defaults = {
            'entity': entity,
            'name': 'test_property',
            'value': 'test value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_test_file_attribute(entity: Optional[Entity] = None, **kwargs) -> EntityAttribute:
        """Create a file attribute with reasonable defaults."""
        if entity is None:
            entity = EntityAttributeSyntheticData.create_test_entity()
        
        # Create test file if not provided
        if 'file_value' not in kwargs:
            test_file = SimpleUploadedFile(
                "test_document.txt",
                b"test file content for synthetic data",
                content_type="text/plain"
            )
            kwargs['file_value'] = test_file
            
        defaults = {
            'entity': entity,
            'name': 'test_document',
            'value': 'Test Document Title',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.FILE),
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_test_secret_attribute(entity: Optional[Entity] = None, **kwargs) -> EntityAttribute:
        """Create a secret attribute with reasonable defaults."""
        if entity is None:
            entity = EntityAttributeSyntheticData.create_test_entity()
            
        defaults = {
            'entity': entity,
            'name': 'api_key',
            'value': 'secret_api_key_12345',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.SECRET),
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_entity_with_mixed_attributes(**entity_kwargs) -> Entity:
        """Create an entity with a variety of attribute types for comprehensive testing."""
        entity = EntityAttributeSyntheticData.create_test_entity(**entity_kwargs)
        
        # Create various attribute types
        EntityAttributeSyntheticData.create_test_text_attribute(
            entity=entity, name='description', value='Test entity for mixed testing'
        )
        EntityAttributeSyntheticData.create_test_secret_attribute(
            entity=entity, name='password', value='super_secret_password'
        )
        EntityAttributeSyntheticData.create_test_file_attribute(
            entity=entity, name='manual', value='Device Manual'
        )
        
        return entity
    
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
    def create_form_data_for_entity_edit(entity: Entity, **overrides) -> Dict[str, Any]:
        """Create complete form data dictionary for entity editing form submissions.
        
        Includes both entity form data and formset data for regular attributes.
        """
        # Entity form data
        form_data = {
            'name': entity.name,
            'entity_type_str': entity.entity_type_str,
        }
        form_data.update(overrides)
        
        # Add formset data for regular attributes (non-file attributes)
        regular_attributes = list(entity.attributes.exclude(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id'))
        
        # Use EntityEditFormHandler as the single source of truth for prefix logic
        prefix = f'entity-{entity.id}'
        
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
    def create_formset_data_for_attributes(attributes: List[EntityAttribute], entity: Entity) -> Dict[str, Any]:
        """Create formset data dictionary for attribute formset submissions."""
        prefix = f'entity-{entity.id}'
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
    def create_file_title_update_data(entity: Entity, file_attributes: List[EntityAttribute]) -> Dict[str, str]:
        """Create POST data for file title updates."""
        data = {}
        for attr in file_attributes:
            field_name = f'file_title_{entity.id}_{attr.id}'
            data[field_name] = f'Updated {attr.name}'
        return data
    
    @staticmethod
    def create_file_deletion_data(file_attributes: List[EntityAttribute]) -> Dict[str, List[str]]:
        """Create POST data for file deletions."""
        return {
            DIVID['ATTR_V2_DELETE_FILE_ATTR']: [str(attr.id) for attr in file_attributes]
        }
    

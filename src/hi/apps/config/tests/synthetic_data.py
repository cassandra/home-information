"""
Synthetic data generators for Subsystem and SubsystemAttribute testing.

Provides centralized, reusable test data creation following the project's
synthetic data pattern documented in test-data-management.md.
"""
import uuid
from django.core.files.uploadedfile import SimpleUploadedFile
from typing import Optional, Dict, Any, List

from hi.constants import DIVID
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.config.models import Subsystem, SubsystemAttribute


class SubsystemAttributeSyntheticData:
    """Centralized synthetic data generators for subsystem attribute testing."""
    
    @staticmethod
    def create_test_subsystem(**kwargs) -> Subsystem:
        """Create a test subsystem with reasonable defaults."""
        # Generate unique name and key to avoid constraint violations
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Subsystem {unique_id}',
            'subsystem_key': f'test_subsystem_{unique_id}',
        }
        defaults.update(kwargs)
        return Subsystem.objects.create(**defaults)
    
    @staticmethod
    def create_test_text_attribute(subsystem: Optional[Subsystem] = None, **kwargs) -> SubsystemAttribute:
        """Create a text attribute with reasonable defaults."""
        if subsystem is None:
            subsystem = SubsystemAttributeSyntheticData.create_test_subsystem()
            
        defaults = {
            'subsystem': subsystem,
            'name': 'test_property',
            'value': 'test value',
            'attribute_type_str': str(AttributeType.PREDEFINED),  # Subsystems typically use PREDEFINED attributes
            'value_type_str': str(AttributeValueType.TEXT),
            'setting_key': 'test.property.key',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_test_secret_attribute(subsystem: Optional[Subsystem] = None, **kwargs) -> SubsystemAttribute:
        """Create a secret attribute with reasonable defaults."""
        if subsystem is None:
            subsystem = SubsystemAttributeSyntheticData.create_test_subsystem()
            
        defaults = {
            'subsystem': subsystem,
            'name': 'api_key',
            'value': 'secret_api_key_12345',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': str(AttributeValueType.SECRET),
            'setting_key': 'api.key.secret',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_test_config_attribute(subsystem: Optional[Subsystem] = None, **kwargs) -> SubsystemAttribute:
        """Create a configuration attribute with reasonable defaults."""
        if subsystem is None:
            subsystem = SubsystemAttributeSyntheticData.create_test_subsystem()
            
        defaults = {
            'subsystem': subsystem,
            'name': 'polling_interval',
            'value': '300',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': str(AttributeValueType.TEXT),
            'setting_key': 'polling.interval.config',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    @staticmethod
    def create_subsystem_with_mixed_attributes(**subsystem_kwargs) -> Subsystem:
        """Create a subsystem with a variety of attribute types for comprehensive testing."""
        subsystem = SubsystemAttributeSyntheticData.create_test_subsystem(**subsystem_kwargs)
        
        # Create various attribute types typical for subsystems
        SubsystemAttributeSyntheticData.create_test_text_attribute(
            subsystem=subsystem, name='endpoint_url', value='https://api.test.com',
            setting_key='endpoint.url.setting'
        )
        SubsystemAttributeSyntheticData.create_test_secret_attribute(
            subsystem=subsystem, name='auth_token', value='super_secret_token',
            setting_key='auth.token.setting'
        )
        SubsystemAttributeSyntheticData.create_test_config_attribute(
            subsystem=subsystem, name='timeout', value='30',
            setting_key='timeout.config.setting'
        )
        
        return subsystem
    
    @staticmethod
    def create_multiple_subsystems_scenario() -> List[Subsystem]:
        """Create multiple subsystems for multi-editing scenario testing."""
        subsystems = []
        
        # Weather subsystem
        weather = SubsystemAttributeSyntheticData.create_test_subsystem(
            name="Weather Service",
            subsystem_key="weather_service"
        )
        SubsystemAttributeSyntheticData.create_test_text_attribute(
            subsystem=weather, name='api_url', value='https://weather.api.com',
            setting_key='weather.api.url'
        )
        SubsystemAttributeSyntheticData.create_test_secret_attribute(
            subsystem=weather, name='api_key', value='weather_api_key',
            setting_key='weather.api.key'
        )
        subsystems.append(weather)
        
        # Another subsystem 
        other = SubsystemAttributeSyntheticData.create_test_subsystem(
            name="Other Service",
            subsystem_key="other_service"
        )
        SubsystemAttributeSyntheticData.create_test_config_attribute(
            subsystem=other, name='refresh_rate', value='60',
            setting_key='other.refresh.rate'
        )
        subsystems.append(other)
        
        return subsystems
    
    @staticmethod
    def create_form_data_for_subsystem_multi_edit(subsystem_list: List[Subsystem], **overrides) -> Dict[str, Any]:
        """Create complete form data dictionary for multi-subsystem editing form submissions.
        
        This handles the complex multi-formset scenario unique to config module.
        """
        form_data = {}
        
        # Add data for each subsystem
        for subsystem in subsystem_list:
            # Get attributes for this subsystem (non-file attributes)
            regular_attributes = list(subsystem.attributes.exclude(
                value_type_str=str(AttributeValueType.FILE)
            ).order_by('id'))
            
            # Use subsystem-specific prefix
            prefix = f'subsystem-{subsystem.id}'
            
            # Formset management form data for this subsystem
            subsystem_formset_data = {
                f'{prefix}-TOTAL_FORMS': str(len(regular_attributes) + 1),  # +1 for empty form
                f'{prefix}-INITIAL_FORMS': str(len(regular_attributes)),
                f'{prefix}-MIN_NUM_FORMS': '0',
                f'{prefix}-MAX_NUM_FORMS': '1000',
            }
            
            # Individual attribute form data for this subsystem
            for i, attr in enumerate(regular_attributes):
                subsystem_formset_data.update({
                    f'{prefix}-{i}-id': str(attr.id),
                    f'{prefix}-{i}-name': attr.name,
                    f'{prefix}-{i}-value': attr.value,
                    f'{prefix}-{i}-attribute_type_str': attr.attribute_type_str,
                })
            
            form_data.update(subsystem_formset_data)
        
        # Apply any overrides
        form_data.update(overrides)
        return form_data
    
    @staticmethod
    def create_form_data_for_single_subsystem_edit(subsystem: Subsystem, **overrides) -> Dict[str, Any]:
        """Create form data for single subsystem editing (simpler scenario)."""
        # Get attributes for this subsystem (non-file attributes)
        regular_attributes = list(subsystem.attributes.exclude(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id'))
        
        # Use subsystem-specific prefix
        prefix = f'subsystem-{subsystem.id}'
        
        # Formset management form data
        form_data = {
            f'{prefix}-TOTAL_FORMS': str(len(regular_attributes) + 1),  # +1 for empty form
            f'{prefix}-INITIAL_FORMS': str(len(regular_attributes)),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }
        
        # Individual attribute form data
        for i, attr in enumerate(regular_attributes):
            form_data.update({
                f'{prefix}-{i}-id': str(attr.id),
                f'{prefix}-{i}-name': attr.name,
                f'{prefix}-{i}-value': attr.value,
                f'{prefix}-{i}-attribute_type_str': attr.attribute_type_str,
            })
        
        # Apply any overrides
        form_data.update(overrides)
        return form_data
    
    @staticmethod
    def create_formset_data_for_attributes(attributes: List[SubsystemAttribute], subsystem: Subsystem) -> Dict[str, Any]:
        """Create formset data dictionary for attribute formset submissions."""
        prefix = f'subsystem-{subsystem.id}'
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
    def create_invalid_form_data_multi_subsystem(subsystem_list: List[Subsystem]) -> Dict[str, Any]:
        """Create invalid form data for multi-subsystem testing."""
        form_data = SubsystemAttributeSyntheticData.create_form_data_for_subsystem_multi_edit(
            subsystem_list
        )
        
        # Make first subsystem's first attribute have invalid data
        if subsystem_list:
            first_subsystem = subsystem_list[0]
            prefix = f'subsystem-{first_subsystem.id}'
            # Set empty name which should be invalid
            form_data[f'{prefix}-0-name'] = ''
            
        return form_data
    
    @staticmethod
    def create_system_configuration_scenario() -> Subsystem:
        """Create a realistic system configuration scenario for testing."""
        subsystem = SubsystemAttributeSyntheticData.create_test_subsystem(
            name="System Configuration",
            subsystem_key="system_config"
        )
        
        # Create system-level configuration attributes
        SubsystemAttributeSyntheticData.create_test_text_attribute(
            subsystem=subsystem,
            name='system_name',
            value='Home Automation System',
            attribute_type_str=str(AttributeType.PREDEFINED),
            setting_key='system.name.config'
        )
        
        SubsystemAttributeSyntheticData.create_test_config_attribute(
            subsystem=subsystem,
            name='log_level',
            value='INFO',
            setting_key='system.log.level'
        )
        
        SubsystemAttributeSyntheticData.create_test_secret_attribute(
            subsystem=subsystem,
            name='encryption_key',
            value='system_encryption_key_123',
            setting_key='system.encryption.key'
        )
        
        return subsystem
    
    @staticmethod
    def create_test_image_file() -> SimpleUploadedFile:
        """Create a test image file for file upload testing."""
        return SimpleUploadedFile(
            "test_config_image.jpg",
            b"fake jpeg image content for testing",
            content_type="image/jpeg"
        )
    
    @staticmethod
    def create_test_config_file() -> SimpleUploadedFile:
        """Create a test configuration file for file upload testing."""
        return SimpleUploadedFile(
            "config.json",
            b'{"test": "configuration", "enabled": true}',
            content_type="application/json"
        )
    

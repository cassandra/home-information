import logging

from hi.apps.entity.enums import (
    EntityType,
    EntityStateType,
    EntityStateValue,
    EntityGroupType,
)
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateType(BaseTestCase):

    def test_template_name_generation(self):
        """Test template name generation logic - could break with refactoring."""
        # Test value template naming
        on_off_template = EntityStateType.ON_OFF.value_template_name()
        self.assertEqual(on_off_template, 'sense/panes/sensor_value_on_off.html')
        
        # Test controller template naming
        temperature_template = EntityStateType.TEMPERATURE.controller_template_name()
        self.assertEqual(temperature_template, 'control/panes/controller_temperature.html')
        
        # Test edge case with underscores
        video_template = EntityStateType.VIDEO_STREAM.value_template_name()
        self.assertEqual(video_template, 'sense/panes/sensor_value_video_stream.html')
        return

    def test_suppress_properties_logic(self):
        """Test suppress display/history logic - business rules that could change."""
        # VIDEO_STREAM has special suppression rules
        self.assertTrue(EntityStateType.VIDEO_STREAM.suppress_display_name)
        self.assertTrue(EntityStateType.VIDEO_STREAM.suppress_history)
        
        # Other types should not suppress
        self.assertFalse(EntityStateType.ON_OFF.suppress_display_name)
        self.assertFalse(EntityStateType.TEMPERATURE.suppress_history)
        return


class TestEntityStateValue(BaseTestCase):

    def test_entity_state_value_choices_mapping(self):
        """Test complex mapping logic between state types and values - prone to bugs."""
        choices = EntityStateValue.entity_state_value_choices()
        
        # Test ON_OFF mapping (values are lowercase strings)
        on_off_choices = choices[EntityStateType.ON_OFF]
        choice_values = [choice[0] for choice in on_off_choices]
        self.assertIn('on', choice_values)
        self.assertIn('off', choice_values)
        self.assertEqual(len(on_off_choices), 2)
        
        # Test CONNECTIVITY mapping (values are lowercase strings)
        connectivity_choices = choices[EntityStateType.CONNECTIVITY]
        choice_values = [choice[0] for choice in connectivity_choices]
        self.assertIn('connected', choice_values)
        self.assertIn('disconnected', choice_values)
        
        # Test MOVEMENT mapping (different values, lowercase)
        movement_choices = choices[EntityStateType.MOVEMENT]
        choice_values = [choice[0] for choice in movement_choices]
        self.assertIn('active', choice_values)
        self.assertIn('idle', choice_values)
        return


class TestEntityGroupType(BaseTestCase):

    def test_from_entity_type_mapping(self):
        """Test entity type to group mapping logic - complex business logic prone to errors."""
        # Test specific mappings that are important for UI grouping
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.LIGHT), EntityGroupType.LIGHTS_SWITCHES)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.CAMERA), EntityGroupType.SECURITY)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.REFRIGERATOR), EntityGroupType.APPLIANCES)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.THERMOSTAT), EntityGroupType.CLIMATE)
        
        # Test fallback to default for unmapped types
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.OTHER), EntityGroupType.OTHER)
        return

    def test_entity_type_set_coverage(self):
        """Test that critical entity types are properly categorized - could break with enum additions."""
        # Test that important entity types are in expected groups
        appliances = EntityGroupType.APPLIANCES
        self.assertIn(EntityType.REFRIGERATOR, appliances.entity_type_set)
        self.assertIn(EntityType.DISHWASHER, appliances.entity_type_set)
        
        security = EntityGroupType.SECURITY
        self.assertIn(EntityType.CAMERA, security.entity_type_set)
        self.assertIn(EntityType.MOTION_SENSOR, security.entity_type_set)
        
        climate = EntityGroupType.CLIMATE
        self.assertIn(EntityType.THERMOSTAT, climate.entity_type_set)
        self.assertIn(EntityType.HVAC_FURNACE, climate.entity_type_set)
        return

import logging

from hi.apps.entity.enums import (
    EntityType,
    EntityStateType,
    EntityGroupType,
)
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateType(BaseTestCase):

    def test_template_name_generation_supports_ui_customization(self):
        """Test template name generation - enables state-specific UI rendering."""
        # Test that different state types generate distinct template paths
        on_off_template = EntityStateType.ON_OFF.value_template_name()
        temperature_template = EntityStateType.TEMPERATURE.value_template_name()
        
        # Should generate different templates for different state types
        self.assertNotEqual(on_off_template, temperature_template)
        
        # Templates should follow consistent naming pattern
        self.assertTrue(on_off_template.startswith('sense/panes/sensor_value_'))
        self.assertTrue(on_off_template.endswith('.html'))
        
        # Controller templates should use different namespace
        controller_template = EntityStateType.TEMPERATURE.controller_template_name()
        self.assertTrue(controller_template.startswith('control/panes/controller_'))
        self.assertTrue(controller_template.endswith('.html'))
        
        # Value and controller templates should be different
        self.assertNotEqual(temperature_template, controller_template)
        
        # Complex state types should work correctly
        multivalued_template = EntityStateType.MULTIVALUED.value_template_name()
        self.assertTrue(multivalued_template.startswith('sense/panes/sensor_value_'))
        self.assertIn('multivalued', multivalued_template)
        
        return


class TestEntityGroupType(BaseTestCase):

    def test_entity_type_to_group_mapping_supports_logical_ui_organization(self):
        """Test entity type to group mapping - organizes entities logically for user interface."""
        # Test that common entity types map to expected functional groups
        
        # Lighting and electrical controls should group together
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.LIGHT),
                         EntityGroupType.LIGHTS_SWITCHES)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.ON_OFF_SWITCH),
                         EntityGroupType.LIGHTS_SWITCHES)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.ELECTRICAL_OUTLET),
                         EntityGroupType.LIGHTS_SWITCHES)
        
        # Security devices should group together
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.CAMERA),
                         EntityGroupType.SECURITY)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.MOTION_SENSOR),
                         EntityGroupType.SECURITY)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.DOOR_LOCK),
                         EntityGroupType.SECURITY)
        
        # Appliances should group together
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.REFRIGERATOR),
                         EntityGroupType.APPLIANCES)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.DISHWASHER),
                         EntityGroupType.APPLIANCES)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.CLOTHES_WASHER),
                         EntityGroupType.APPLIANCES)
        
        # Climate control devices should group together
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.THERMOSTAT),
                         EntityGroupType.CLIMATE)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.HVAC_FURNACE),
                         EntityGroupType.CLIMATE)
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.HUMIDIFIER),
                         EntityGroupType.CLIMATE)
        
        # Test fallback behavior for unmapped types
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.OTHER),
                         EntityGroupType.OTHER)
        
        return

    def test_entity_group_sets_provide_comprehensive_categorization(self):
        """Test entity type set coverage - ensures all important device types are properly categorized."""
        # Test that major appliance categories are well-represented
        appliances = EntityGroupType.APPLIANCES
        expected_appliances = [
            EntityType.REFRIGERATOR,
            EntityType.DISHWASHER, 
            EntityType.CLOTHES_WASHER,
            EntityType.CLOTHES_DRYER,
            EntityType.MICROWAVE_OVEN,
            EntityType.WATER_HEATER
        ]
        
        for appliance_type in expected_appliances:
            self.assertIn(appliance_type, appliances.entity_type_set,
                          f"{appliance_type} should be in APPLIANCES group")
        
        # Test that security devices are comprehensively covered
        security = EntityGroupType.SECURITY
        expected_security = [
            EntityType.CAMERA,
            EntityType.MOTION_SENSOR,
            EntityType.DOOR_LOCK,
            EntityType.PRESENCE_SENSOR,
            EntityType.OPEN_CLOSE_SENSOR
        ]
        
        for security_type in expected_security:
            self.assertIn(security_type, security.entity_type_set,
                          f"{security_type} should be in SECURITY group")
        
        # Test that climate control devices are well-categorized
        climate = EntityGroupType.CLIMATE
        expected_climate = [
            EntityType.THERMOSTAT,
            EntityType.HVAC_FURNACE,
            EntityType.HVAC_AIR_HANDLER,
            EntityType.HUMIDIFIER,
            EntityType.THERMOMETER
        ]
        
        for climate_type in expected_climate:
            self.assertIn(climate_type, climate.entity_type_set,
                          f"{climate_type} should be in CLIMATE group")
        
        # Test that no entity type appears in multiple groups (mutual exclusivity)
        all_groups = list(EntityGroupType)
        all_entity_types_in_groups = set()
        
        for group in all_groups:
            # Check for overlaps
            overlap = all_entity_types_in_groups.intersection(group.entity_type_set)
            self.assertEqual(len(overlap), 0,
                             f"Group {group} has overlapping entity types: {overlap}")
            all_entity_types_in_groups.update(group.entity_type_set)
        
        return

    def test_entity_group_fallback_logic_handles_unmapped_types(self):
        """Test entity group fallback behavior - provides sensible defaults for edge cases."""
        # Test that unknown entity types fall back to OTHER group
        other_group = EntityGroupType.from_entity_type(EntityType.OTHER)
        self.assertEqual(other_group, EntityGroupType.OTHER)
        
        # Test that the OTHER group contains the OTHER entity type
        self.assertIn(EntityType.OTHER, EntityGroupType.OTHER.entity_type_set)
        
        # Test that the default class method returns OTHER
        default_group = EntityGroupType.default()
        self.assertEqual(default_group, EntityGroupType.OTHER)
        
        # Test consistency between from_entity_type fallback and default
        self.assertEqual(EntityGroupType.from_entity_type(EntityType.OTHER),
                         EntityGroupType.default())
        
        return

    def test_entity_group_labels_support_user_friendly_display(self):
        """Test entity group labels - provide meaningful names for UI display."""
        # Test that all groups have meaningful labels
        expected_labels = {
            EntityGroupType.APPLIANCES: 'Appliances',
            EntityGroupType.SECURITY: 'Security', 
            EntityGroupType.CLIMATE: 'Climate',
            EntityGroupType.LIGHTS_SWITCHES: 'Lights, Switches, Outlets',
            EntityGroupType.COMPUTER_NETWORK: 'Computer/Network',
            EntityGroupType.AUDIO_VISUAL: 'Audio/Visual'
        }
        
        for group, expected_label in expected_labels.items():
            self.assertEqual(group.label, expected_label,
                             f"{group} should have label '{expected_label}'")
        
        # Test that all group labels are non-empty strings
        for group in EntityGroupType:
            self.assertIsInstance(group.label, str)
            self.assertGreater(len(group.label), 0)
            
        # Test that labels are unique (no duplicates)
        all_labels = [group.label for group in EntityGroupType]
        unique_labels = set(all_labels)
        self.assertEqual(len(all_labels), len(unique_labels),
                         "All group labels should be unique")
        
        return

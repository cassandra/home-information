import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.monitor.status_display_data import StatusDisplayData
from hi.apps.monitor.transient_models import EntityStateStatusData
from hi.hi_styles import StatusStyle
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestStatusDisplayData(BaseTestCase):
    """Test StatusDisplayData business logic and style calculations."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='SENSOR'
        )

    def _create_entity_state_status_data(self, entity_state_type_str, sensor_responses=None):
        """Helper to create EntityStateStatusData with mock sensor responses."""
        entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str=entity_state_type_str
        )
        
        sensor_response_list = sensor_responses or []
        controller_data_list = []
        
        return EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=sensor_response_list,
            controller_data_list=controller_data_list
        )

    def _create_mock_sensor_response(self, value, timestamp=None):
        """Helper to create mock sensor response with value and timestamp."""
        response = Mock(spec=SensorResponse)
        response.value = value
        response.timestamp = timestamp or datetime.now()
        return response

    # ON_OFF State Type Tests
    
    def test_on_off_state_returns_on_style(self):
        """Test ON_OFF state returns On style when value is ON."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ON))
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.On)
        self.assertFalse(display_data.should_skip)

    def test_on_off_state_returns_off_style(self):
        """Test ON_OFF state returns Off style when value is OFF."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.OFF))
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Off)
        self.assertFalse(display_data.should_skip)

    def test_on_off_state_returns_none_for_invalid_value(self):
        """Test ON_OFF state returns None for invalid values."""
        sensor_response = self._create_mock_sensor_response('INVALID')
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertIsNone(display_data.svg_status_style)
        self.assertTrue(display_data.should_skip)

    # CONNECTIVITY State Type Tests
    
    def test_connectivity_state_returns_connected_style(self):
        """Test CONNECTIVITY state returns Connected style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.CONNECTED))
        status_data = self._create_entity_state_status_data('CONNECTIVITY', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Connected)

    def test_connectivity_state_returns_disconnected_style(self):
        """Test CONNECTIVITY state returns Disconnected style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.DISCONNECTED))
        status_data = self._create_entity_state_status_data('CONNECTIVITY', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Disconnected)

    # HIGH_LOW State Type Tests
    
    def test_high_low_state_returns_high_style(self):
        """Test HIGH_LOW state returns High style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.HIGH))
        status_data = self._create_entity_state_status_data('HIGH_LOW', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.High)

    def test_high_low_state_returns_low_style(self):
        """Test HIGH_LOW state returns Low style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.LOW))
        status_data = self._create_entity_state_status_data('HIGH_LOW', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Low)

    # MOVEMENT State Type Tests with Time Thresholds
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_active_returns_movement_active(self, mock_now):
        """Test MOVEMENT state returns MovementActive for current active state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ACTIVE))
        status_data = self._create_entity_state_status_data('MOVEMENT', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementActive)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_recent_within_threshold(self, mock_now):
        """Test MOVEMENT state returns MovementRecent for recently active state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        
        # Penultimate was active 60 seconds ago (within 90 second threshold)
        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.IDLE),
            base_time
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.ACTIVE),
            base_time - timedelta(seconds=60)
        )
        
        status_data = self._create_entity_state_status_data('MOVEMENT', [recent_response, past_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_past_within_threshold(self, mock_now):
        """Test MOVEMENT state returns MovementPast for past active state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        
        # Penultimate was active 120 seconds ago (between 90-180 second threshold)
        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.IDLE),
            base_time
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.ACTIVE),
            base_time - timedelta(seconds=120)
        )
        
        status_data = self._create_entity_state_status_data('MOVEMENT', [recent_response, past_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementPast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_idle_beyond_threshold(self, mock_now):
        """Test MOVEMENT state returns MovementIdle beyond all thresholds."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        
        # Penultimate was active 200 seconds ago (beyond 180 second threshold)
        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.IDLE),
            base_time
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.ACTIVE),
            base_time - timedelta(seconds=200)
        )
        
        status_data = self._create_entity_state_status_data('MOVEMENT', [recent_response, past_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementIdle)

    # PRESENCE State Type Tests (similar to movement)
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_presence_state_active_returns_movement_active(self, mock_now):
        """Test PRESENCE state returns MovementActive for current active state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ACTIVE))
        status_data = self._create_entity_state_status_data('PRESENCE', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        # PRESENCE reuses Movement styles in the implementation
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementActive)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_presence_state_inactive_returns_movement_idle(self, mock_now):
        """Test PRESENCE state returns MovementIdle for inactive state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.IDLE))
        status_data = self._create_entity_state_status_data('PRESENCE', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        # Should return MovementIdle for inactive presence
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementIdle)

    # OPEN_CLOSE State Type Tests with Time Thresholds
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_open_returns_open(self, mock_now):
        """Test OPEN_CLOSE state returns Open for current open state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.OPEN))
        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Open)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_recent_within_threshold(self, mock_now):
        """Test OPEN_CLOSE state returns OpenRecent for recently open state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        
        # Was open 60 seconds ago (within 90 second threshold)
        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.CLOSED),
            base_time
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.OPEN),
            base_time - timedelta(seconds=60)
        )
        
        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [recent_response, past_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.OpenRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_past_within_threshold(self, mock_now):
        """Test OPEN_CLOSE state returns OpenPast for past open state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        
        # Was open 120 seconds ago (between 90-180 second threshold)
        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.CLOSED),
            base_time
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.OPEN),
            base_time - timedelta(seconds=120)
        )
        
        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [recent_response, past_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.OpenPast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_closed_beyond_threshold(self, mock_now):
        """Test OPEN_CLOSE state returns Closed beyond all thresholds."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        
        # Was open 200 seconds ago (beyond 180 second threshold)
        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.CLOSED),
            base_time
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.OPEN),
            base_time - timedelta(seconds=200)
        )
        
        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [recent_response, past_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Closed)

    # Edge Cases and Default Behavior Tests
    
    def test_no_sensor_data_returns_default_style(self):
        """Test default style is returned when no sensor data exists."""
        status_data = self._create_entity_state_status_data('TEMPERATURE', [])
        
        display_data = StatusDisplayData(status_data)
        
        # Should use default style with DEFAULT_STATUS_VALUE when no sensor data
        self.assertIsNotNone(display_data.svg_status_style)
        # The style will be created via StatusStyle.default()

    def test_unmapped_entity_type_returns_default_style(self):
        """Test unmapped entity types return default style with sensor value."""
        sensor_response = self._create_mock_sensor_response('25.5')
        status_data = self._create_entity_state_status_data('TEMPERATURE', [sensor_response])
        
        with patch.object(StatusStyle, 'default') as mock_default:
            expected_style = Mock()
            mock_default.return_value = expected_style
            
            display_data = StatusDisplayData(status_data)
            
            mock_default.assert_called_once_with(status_value='25.5')
            self.assertEqual(display_data.svg_status_style, expected_style)

    def test_single_sensor_value_handles_penultimate_gracefully(self):
        """Test single sensor value doesn't break penultimate access."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.IDLE))
        status_data = self._create_entity_state_status_data('MOVEMENT', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        # Should return idle since no penultimate active state
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementIdle)
        self.assertIsNone(display_data.penultimate_sensor_value)
        self.assertIsNone(display_data.penultimate_sensor_timestamp)

    # Property Access Tests
    
    def test_css_class_delegates_to_entity_state(self):
        """Test css_class property delegates to entity_state."""
        status_data = self._create_entity_state_status_data('ON_OFF', [])
        display_data = StatusDisplayData(status_data)
        
        # Entity state css_class should be accessible
        css_class = display_data.css_class
        self.assertIsNotNone(css_class)
        self.assertIn('hi-entity-state', css_class)  # Expected format from entity_state

    def test_attribute_dict_returns_style_dict_when_present(self):
        """Test attribute_dict returns style dictionary when style exists."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ON))
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        # Should return the style's to_dict() result
        attr_dict = display_data.attribute_dict
        self.assertIsInstance(attr_dict, dict)
        self.assertGreater(len(attr_dict), 0)

    def test_attribute_dict_returns_empty_when_no_style(self):
        """Test attribute_dict returns empty dict when no style."""
        sensor_response = self._create_mock_sensor_response('INVALID')
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.attribute_dict, {})

    def test_latest_sensor_value_extraction(self):
        """Test latest_sensor_value extracts first response value."""
        response1 = self._create_mock_sensor_response('VALUE1')
        response2 = self._create_mock_sensor_response('VALUE2')
        status_data = self._create_entity_state_status_data('ON_OFF', [response1, response2])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.latest_sensor_value, 'VALUE1')

    def test_penultimate_sensor_value_extraction(self):
        """Test penultimate_sensor_value extracts second response value."""
        response1 = self._create_mock_sensor_response('VALUE1')
        response2 = self._create_mock_sensor_response('VALUE2')
        status_data = self._create_entity_state_status_data('ON_OFF', [response1, response2])
        
        display_data = StatusDisplayData(status_data)
        
        self.assertEqual(display_data.penultimate_sensor_value, 'VALUE2')

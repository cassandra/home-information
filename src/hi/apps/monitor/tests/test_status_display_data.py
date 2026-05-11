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

    # SMOKE State Type Tests with Time Thresholds
    #
    # Mirrors the movement decay pattern but with longer thresholds
    # (10 min recent / 30 min past) since fire events have higher
    # operator significance and the visual reminder should linger.

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_detected_returns_smoke_detected(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)

        sensor_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED)
        )
        status_data = self._create_entity_state_status_data('SMOKE', [sensor_response])

        display_data = StatusDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokeDetected)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_recent_within_threshold(self, mock_now):
        # Penultimate detected 5 minutes ago (within the 10-minute
        # RECENT threshold); current is clear.
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_CLEAR), base_time,
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED),
            base_time - timedelta(seconds=300),
        )

        status_data = self._create_entity_state_status_data(
            'SMOKE', [recent_response, past_response],
        )

        display_data = StatusDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokeRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_past_beyond_recent_within_past(self, mock_now):
        # Penultimate detected 20 minutes ago (between RECENT 10
        # min and PAST 30 min thresholds).
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_CLEAR), base_time,
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED),
            base_time - timedelta(seconds=1200),
        )

        status_data = self._create_entity_state_status_data(
            'SMOKE', [recent_response, past_response],
        )

        display_data = StatusDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokePast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_clear_after_past_threshold(self, mock_now):
        # Penultimate detected 1 hour ago (beyond PAST 30 min).
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        recent_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_CLEAR), base_time,
        )
        past_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED),
            base_time - timedelta(seconds=3600),
        )

        status_data = self._create_entity_state_status_data(
            'SMOKE', [recent_response, past_response],
        )

        display_data = StatusDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokeClear)

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

    # OPEN_CLOSE_POSITION State Type Tests (continuous-position cover)

    def test_open_close_position_zero_returns_closed_style(self):
        sensor_response = self._create_mock_sensor_response('0')
        status_data = self._create_entity_state_status_data(
            'OPEN_CLOSE_POSITION', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style, StatusStyle.Closed )

    def test_open_close_position_partial_returns_open_partial_style(self):
        # Mid-range positions land in the partial bucket, mirroring
        # the dimmer's three-bucket discretization.
        for position in ( '1', '50', '74' ):
            with self.subTest( position=position ):
                sensor_response = self._create_mock_sensor_response( position )
                status_data = self._create_entity_state_status_data(
                    'OPEN_CLOSE_POSITION', [ sensor_response ],
                )

                display_data = StatusDisplayData( status_data )

                self.assertEqual( display_data.svg_status_style, StatusStyle.OpenPartial )

    def test_open_close_position_high_returns_open_style(self):
        for position in ( '75', '90', '100' ):
            with self.subTest( position=position ):
                sensor_response = self._create_mock_sensor_response( position )
                status_data = self._create_entity_state_status_data(
                    'OPEN_CLOSE_POSITION', [ sensor_response ],
                )

                display_data = StatusDisplayData( status_data )

                self.assertEqual( display_data.svg_status_style, StatusStyle.Open )

    def test_open_close_position_non_numeric_returns_closed_style(self):
        # Defensive: a malformed value shouldn't crash the
        # display path; treat as closed.
        sensor_response = self._create_mock_sensor_response( 'garbage' )
        status_data = self._create_entity_state_status_data(
            'OPEN_CLOSE_POSITION', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style, StatusStyle.Closed )

    # POWER_LEVEL State Type Tests (continuous-percentage controller)
    # Reuses StatusStyle.light_dimmer for bucketing: <15 off,
    # 15-84 dim, >=85 on. Verify the bucket boundaries and the
    # graceful path for malformed values.

    def test_power_level_zero_returns_off_bucket(self):
        sensor_response = self._create_mock_sensor_response( '0' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'off' )

    def test_power_level_low_returns_dim_bucket_at_threshold(self):
        # 15 is the off→dim boundary.
        sensor_response = self._create_mock_sensor_response( '15' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'dim' )

    def test_power_level_mid_returns_dim_bucket(self):
        sensor_response = self._create_mock_sensor_response( '50' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'dim' )

    def test_power_level_high_returns_on_bucket_at_threshold(self):
        # 85 is the dim→on boundary.
        sensor_response = self._create_mock_sensor_response( '85' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'on' )

    def test_power_level_full_returns_on_bucket(self):
        sensor_response = self._create_mock_sensor_response( '100' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'on' )

    def test_power_level_non_numeric_falls_to_off_bucket(self):
        # Defensive: a malformed value shouldn't crash the
        # display path; treat as off (value=0).
        sensor_response = self._create_mock_sensor_response( 'garbage' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = StatusDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'off' )

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


class TestLatestDisplayLabel(BaseTestCase):
    """``latest_display_label`` is the universal source of truth for
    the polling-refresh display text. Unit-bearing states get the
    combined ``DisplayValue`` string; unit-less enum states get the
    labeled form; unit-less numeric / free-form passes through."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='SENSOR',
        )

    def _make_display_data(self, entity_state_type_str, value, units=None):
        entity_state = EntityState.objects.create(
            entity = self.entity,
            entity_state_type_str = entity_state_type_str,
            units = units,
        )
        response = Mock(spec=SensorResponse)
        response.value = value
        response.timestamp = datetime.now()
        status_data = EntityStateStatusData(
            entity_state = entity_state,
            sensor_response_list = [ response ],
            controller_data_list = [],
        )
        return StatusDisplayData( status_data )

    def test_unit_less_enum_value_returns_labeled_form(self):
        # ``smoke_detected`` (wire form) → ``Smoke Detected``
        # (human-readable label) — matches what the ``value_label``
        # template filter produces on initial render.
        display_data = self._make_display_data(
            'SMOKE', str(EntityStateValue.SMOKE_DETECTED),
        )
        self.assertEqual( display_data.latest_display_label, 'Smoke Detected' )

    def test_unit_less_enum_movement_active_returns_active(self):
        display_data = self._make_display_data(
            'MOVEMENT', str(EntityStateValue.ACTIVE),
        )
        self.assertEqual( display_data.latest_display_label, 'Active' )

    def test_unit_bearing_temperature_returns_combined_form(self):
        # Stored canonical °C; default display unit is °F unless
        # the test environment overrides. The exact magnitude depends
        # on the user-preference test default — pin the structural
        # contract (non-empty string containing a temperature unit
        # symbol) rather than the exact magnitude.
        display_data = self._make_display_data(
            'TEMPERATURE', '21', units = '°C',
        )
        label = display_data.latest_display_label
        self.assertTrue( label )
        self.assertTrue(
            '°F' in label or '°C' in label,
            f'expected temperature unit symbol in label, got {label!r}',
        )

    def test_unit_less_numeric_passes_through(self):
        # A POWER_LEVEL or LIGHT_DIMMER raw value like ``"75"`` isn't
        # an enum member; the label must equal the input unchanged.
        display_data = self._make_display_data( 'POWER_LEVEL', '75' )
        self.assertEqual( display_data.latest_display_label, '75' )

    def test_empty_value_returns_empty_string(self):
        # Defensive: a sensor with no responses yet has empty
        # latest_sensor_value → label is empty (no crash, no enum
        # lookup attempt).
        entity_state = EntityState.objects.create(
            entity = self.entity, entity_state_type_str = 'MOVEMENT',
        )
        status_data = EntityStateStatusData(
            entity_state = entity_state,
            sensor_response_list = [],
            controller_data_list = [],
        )
        display_data = StatusDisplayData( status_data )
        self.assertEqual( display_data.latest_display_label, '' )


class TestToPollingUpdateDict(BaseTestCase):
    """``to_polling_update_dict`` builds the per-EntityState row of
    the unified ``entityStateStatusMap``. Pins the contract for
    each kind of EntityState the polling path sees: sensor-only
    (no ``controller`` key), unit-bearing (``magnitude`` and
    ``unit_symbol`` present in display_value), unit-less enum
    (``magnitude``/``unit_symbol`` absent), and the always-present
    ``attributes`` and ``display_value`` keys."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name = 'Test Entity', entity_type_str = 'SENSOR',
        )

    def _make_display_data(self, entity_state_type_str, value,
                           units=None, with_controller=False):
        entity_state = EntityState.objects.create(
            entity = self.entity,
            entity_state_type_str = entity_state_type_str,
            units = units,
        )
        response = Mock(spec=SensorResponse)
        response.value = value
        response.timestamp = datetime.now()
        controller_data_list = []
        if with_controller:
            controller = Mock()
            controller.entity_state = entity_state
            controller_data_list = [ Mock(controller=controller) ]
        status_data = EntityStateStatusData(
            entity_state = entity_state,
            sensor_response_list = [ response ],
            controller_data_list = controller_data_list,
        )
        return StatusDisplayData( status_data )

    def test_sensor_only_row_omits_controller_key(self):
        display_data = self._make_display_data(
            'MOVEMENT', str(EntityStateValue.ACTIVE),
        )
        row = display_data.to_polling_update_dict()
        self.assertNotIn( 'controller', row )

    def test_controller_bearing_row_has_controller_value_dict(self):
        display_data = self._make_display_data(
            'ON_OFF', str(EntityStateValue.ON), with_controller=True,
        )
        row = display_data.to_polling_update_dict()
        self.assertIn( 'controller', row )
        self.assertIn( 'value', row[ 'controller' ] )

    def test_unit_bearing_display_value_includes_magnitude_and_unit(self):
        display_data = self._make_display_data(
            'TEMPERATURE', '21', units = '°C',
        )
        row = display_data.to_polling_update_dict()
        display_value = row[ 'display_value' ]
        self.assertIn( 'text', display_value )
        self.assertIn( 'magnitude', display_value )
        self.assertIn( 'unit_symbol', display_value )

    def test_unit_less_display_value_omits_magnitude_and_unit(self):
        display_data = self._make_display_data(
            'MOVEMENT', str(EntityStateValue.ACTIVE),
        )
        row = display_data.to_polling_update_dict()
        display_value = row[ 'display_value' ]
        self.assertIn( 'text', display_value )
        self.assertNotIn( 'magnitude', display_value )
        self.assertNotIn( 'unit_symbol', display_value )

    def test_display_value_text_is_human_readable_label(self):
        # Same source of truth as ``value_label`` template filter —
        # JS sets element.textContent to this string.
        display_data = self._make_display_data(
            'SMOKE', str(EntityStateValue.SMOKE_DETECTED),
        )
        row = display_data.to_polling_update_dict()
        self.assertEqual(
            row[ 'display_value' ][ 'text' ], 'Smoke Detected',
        )

    def test_display_value_text_humanizes_free_form_wire_value(self):
        # DISCRETE-typed states (HA hvac_action, fan preset, etc.)
        # carry free-form wire values not bound to an
        # EntityStateValue member. The polling map's
        # ``display_value.text`` humanizes them so the sensor card
        # displays a readable label on poll refresh — the headline
        # behavior of #310.
        display_data = self._make_display_data( 'DISCRETE', 'heating' )
        row = display_data.to_polling_update_dict()
        self.assertEqual(
            row[ 'display_value' ][ 'text' ], 'Heating',
        )

    def test_attributes_always_present(self):
        # Even for unrecognized values where there's no SVG style,
        # ``attributes`` is always emitted (possibly as an empty
        # dict) — the JS dispatcher iterates whatever keys it
        # finds and is safe with an empty mapping.
        display_data = self._make_display_data( 'ON_OFF', 'INVALID' )
        row = display_data.to_polling_update_dict()
        self.assertIn( 'attributes', row )
        self.assertIsInstance( row[ 'attributes' ], dict )

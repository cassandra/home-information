import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.monitor.display_data import (
    EntityStateDisplayData,
    RecentStateValueSummary,
    StateValueEntry,
)
from hi.apps.monitor.status_data import EntityStateStatusData
from hi.hi_styles import StatusStyle
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateDisplayData(BaseTestCase):
    """Test EntityStateDisplayData business logic and style calculations."""

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
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.On)
        self.assertFalse(display_data.should_skip)

    def test_on_off_state_returns_off_style(self):
        """Test ON_OFF state returns Off style when value is OFF."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.OFF))
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Off)
        self.assertFalse(display_data.should_skip)

    def test_on_off_state_returns_none_for_invalid_value(self):
        """Test ON_OFF state returns None for invalid values."""
        sensor_response = self._create_mock_sensor_response('INVALID')
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertIsNone(display_data.svg_status_style)
        self.assertTrue(display_data.should_skip)

    # CONNECTIVITY State Type Tests
    
    def test_connectivity_state_returns_connected_style(self):
        """Test CONNECTIVITY state returns Connected style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.CONNECTED))
        status_data = self._create_entity_state_status_data('CONNECTIVITY', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Connected)

    def test_connectivity_state_returns_disconnected_style(self):
        """Test CONNECTIVITY state returns Disconnected style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.DISCONNECTED))
        status_data = self._create_entity_state_status_data('CONNECTIVITY', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Disconnected)

    # HIGH_LOW State Type Tests
    
    def test_high_low_state_returns_high_style(self):
        """Test HIGH_LOW state returns High style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.HIGH))
        status_data = self._create_entity_state_status_data('HIGH_LOW', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.High)

    def test_high_low_state_returns_low_style(self):
        """Test HIGH_LOW state returns Low style."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.LOW))
        status_data = self._create_entity_state_status_data('HIGH_LOW', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Low)

    # MOVEMENT State Type Tests with Time Thresholds
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_active_returns_movement_active(self, mock_now):
        """Test MOVEMENT state returns MovementActive for current active state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ACTIVE))
        status_data = self._create_entity_state_status_data('MOVEMENT', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementActive)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_recent_within_threshold(self, mock_now):
        """Test MOVEMENT state returns MovementRecent for recently active state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        # Decay is anchored on when the event ENDED (the latest, post-event
        # transition), not when it started. Movement ended (returned to idle)
        # 60s ago — within the 90s recent window — even though it began long
        # before that. Start-anchoring would mis-classify this as idle.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.IDLE),
            base_time - timedelta(seconds=60)
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.ACTIVE),
            base_time - timedelta(seconds=600)
        )

        status_data = self._create_entity_state_status_data('MOVEMENT', [latest_response, prior_response])

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_past_within_threshold(self, mock_now):
        """Test MOVEMENT state returns MovementPast for past active state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        # Movement ended 120s ago (between the 90s recent and 180s past
        # thresholds); it began long before. Start-anchoring would call
        # this idle.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.IDLE),
            base_time - timedelta(seconds=120)
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.ACTIVE),
            base_time - timedelta(seconds=600)
        )

        status_data = self._create_entity_state_status_data('MOVEMENT', [latest_response, prior_response])

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementPast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_movement_state_idle_beyond_threshold(self, mock_now):
        """Test MOVEMENT state returns MovementIdle beyond all thresholds."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        # Movement ended 200s ago — beyond the 180s past threshold — so the
        # decay has fully elapsed and it reads idle again.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.IDLE),
            base_time - timedelta(seconds=200)
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.ACTIVE),
            base_time - timedelta(seconds=600)
        )

        status_data = self._create_entity_state_status_data('MOVEMENT', [latest_response, prior_response])

        display_data = EntityStateDisplayData(status_data)

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

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokeDetected)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_recent_within_threshold(self, mock_now):
        # Smoke cleared 5 minutes ago (within the 10-minute RECENT
        # threshold), having been detected long before. Decay anchors on
        # the clear (event end), so start-anchoring would call this clear.
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_CLEAR),
            base_time - timedelta(seconds=300),
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED),
            base_time - timedelta(seconds=5400),
        )

        status_data = self._create_entity_state_status_data(
            'SMOKE', [latest_response, prior_response],
        )

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokeRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_past_beyond_recent_within_past(self, mock_now):
        # Smoke cleared 20 minutes ago (between the RECENT 10-min and PAST
        # 30-min thresholds), having been detected long before.
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_CLEAR),
            base_time - timedelta(seconds=1200),
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED),
            base_time - timedelta(seconds=5400),
        )

        status_data = self._create_entity_state_status_data(
            'SMOKE', [latest_response, prior_response],
        )

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokePast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_smoke_state_clear_after_past_threshold(self, mock_now):
        # Smoke cleared 40 minutes ago — beyond the PAST 30-min threshold —
        # so the decay has fully elapsed and it reads clear.
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_CLEAR),
            base_time - timedelta(seconds=2400),
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.SMOKE_DETECTED),
            base_time - timedelta(seconds=5400),
        )

        status_data = self._create_entity_state_status_data(
            'SMOKE', [latest_response, prior_response],
        )

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.SmokeClear)

    # PRESENCE State Type Tests (similar to movement)
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_presence_state_active_returns_movement_active(self, mock_now):
        """Test PRESENCE state returns MovementActive for current active state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ACTIVE))
        status_data = self._create_entity_state_status_data('PRESENCE', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        # PRESENCE reuses Movement styles in the implementation
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementActive)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_presence_state_inactive_returns_movement_idle(self, mock_now):
        """Test PRESENCE state returns MovementIdle for inactive state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.IDLE))
        status_data = self._create_entity_state_status_data('PRESENCE', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        # Should return MovementIdle for inactive presence
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementIdle)

    # OBJECT_PRESENCE State Type Tests
    #
    # Same decay thresholds as MOVEMENT, but the "active" discriminator
    # is "value is not OBJECT_NONE" (any detected class counts).

    @patch('hi.apps.common.datetimeproxy.now')
    def test_object_presence_detected_returns_movement_active(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        sensor_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_PERSON),
        )
        status_data = self._create_entity_state_status_data(
            'OBJECT_PRESENCE', [sensor_response],
        )
        display_data = EntityStateDisplayData(status_data)
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementActive)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_object_presence_other_class_also_active(self, mock_now):
        # Any non-NONE class — including OTHER — keeps the style active.
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        sensor_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_OTHER),
        )
        status_data = self._create_entity_state_status_data(
            'OBJECT_PRESENCE', [sensor_response],
        )
        display_data = EntityStateDisplayData(status_data)
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementActive)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_object_presence_recent_within_threshold(self, mock_now):
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        # Detection cleared (returned to NONE) 60s ago (within RECENT 90s),
        # having begun long before. Start-anchoring would call this idle.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_NONE),
            base_time - timedelta(seconds=60),
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_ANIMAL),
            base_time - timedelta(seconds=600),
        )
        status_data = self._create_entity_state_status_data(
            'OBJECT_PRESENCE', [latest_response, prior_response],
        )
        display_data = EntityStateDisplayData(status_data)
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_object_presence_past_within_threshold(self, mock_now):
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        # Detection cleared 120s ago (between the 90s and 180s thresholds),
        # having begun long before.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_NONE),
            base_time - timedelta(seconds=120),
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_CAR),
            base_time - timedelta(seconds=600),
        )
        status_data = self._create_entity_state_status_data(
            'OBJECT_PRESENCE', [latest_response, prior_response],
        )
        display_data = EntityStateDisplayData(status_data)
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementPast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_object_presence_idle_beyond_threshold(self, mock_now):
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time
        # Detection cleared 200s ago — beyond the PAST 180s threshold — so
        # the decay has fully elapsed and it reads idle.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_NONE),
            base_time - timedelta(seconds=200),
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.OBJECT_PACKAGE),
            base_time - timedelta(seconds=600),
        )
        status_data = self._create_entity_state_status_data(
            'OBJECT_PRESENCE', [latest_response, prior_response],
        )
        display_data = EntityStateDisplayData(status_data)
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementIdle)

    # OPEN_CLOSE State Type Tests with Time Thresholds
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_open_returns_open(self, mock_now):
        """Test OPEN_CLOSE state returns Open for current open state."""
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.OPEN))
        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.svg_status_style, StatusStyle.Open)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_recent_within_threshold(self, mock_now):
        """Test OPEN_CLOSE state returns OpenRecent for recently open state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        # Closed 60 seconds ago (within the 90s recent window) after having
        # been open for a long time. Decay anchors on the close (event end),
        # so a long open no longer suppresses the "recently open" cue.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.CLOSED),
            base_time - timedelta(seconds=60)
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.OPEN),
            base_time - timedelta(seconds=600)
        )

        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [latest_response, prior_response])

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.OpenRecent)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_past_within_threshold(self, mock_now):
        """Test OPEN_CLOSE state returns OpenPast for past open state."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        # Closed 120 seconds ago (between the 90s and 180s thresholds) after
        # having been open for a long time.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.CLOSED),
            base_time - timedelta(seconds=120)
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.OPEN),
            base_time - timedelta(seconds=600)
        )

        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [latest_response, prior_response])

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.OpenPast)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_open_close_state_closed_beyond_threshold(self, mock_now):
        """Test OPEN_CLOSE state returns Closed beyond all thresholds."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_now.return_value = base_time

        # Closed 200 seconds ago — beyond the 180s past threshold — so the
        # decay has fully elapsed and it reads closed.
        latest_response = self._create_mock_sensor_response(
            str(EntityStateValue.CLOSED),
            base_time - timedelta(seconds=200)
        )
        prior_response = self._create_mock_sensor_response(
            str(EntityStateValue.OPEN),
            base_time - timedelta(seconds=600)
        )

        status_data = self._create_entity_state_status_data('OPEN_CLOSE', [latest_response, prior_response])

        display_data = EntityStateDisplayData(status_data)

        self.assertEqual(display_data.svg_status_style, StatusStyle.Closed)

    # OPEN_CLOSE_POSITION State Type Tests (continuous-position cover)

    def test_open_close_position_zero_returns_closed_style(self):
        sensor_response = self._create_mock_sensor_response('0')
        status_data = self._create_entity_state_status_data(
            'OPEN_CLOSE_POSITION', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

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

                display_data = EntityStateDisplayData( status_data )

                self.assertEqual( display_data.svg_status_style, StatusStyle.OpenPartial )

    def test_open_close_position_high_returns_open_style(self):
        for position in ( '75', '90', '100' ):
            with self.subTest( position=position ):
                sensor_response = self._create_mock_sensor_response( position )
                status_data = self._create_entity_state_status_data(
                    'OPEN_CLOSE_POSITION', [ sensor_response ],
                )

                display_data = EntityStateDisplayData( status_data )

                self.assertEqual( display_data.svg_status_style, StatusStyle.Open )

    def test_open_close_position_non_numeric_returns_closed_style(self):
        # Defensive: a malformed value shouldn't crash the
        # display path; treat as closed.
        sensor_response = self._create_mock_sensor_response( 'garbage' )
        status_data = self._create_entity_state_status_data(
            'OPEN_CLOSE_POSITION', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

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

        display_data = EntityStateDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'off' )

    def test_power_level_low_returns_dim_bucket_at_threshold(self):
        # 15 is the off→dim boundary.
        sensor_response = self._create_mock_sensor_response( '15' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'dim' )

    def test_power_level_mid_returns_dim_bucket(self):
        sensor_response = self._create_mock_sensor_response( '50' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'dim' )

    def test_power_level_high_returns_on_bucket_at_threshold(self):
        # 85 is the dim→on boundary.
        sensor_response = self._create_mock_sensor_response( '85' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'on' )

    def test_power_level_full_returns_on_bucket(self):
        sensor_response = self._create_mock_sensor_response( '100' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'on' )

    def test_power_level_non_numeric_falls_to_off_bucket(self):
        # Defensive: a malformed value shouldn't crash the
        # display path; treat as off (value=0).
        sensor_response = self._create_mock_sensor_response( 'garbage' )
        status_data = self._create_entity_state_status_data(
            'POWER_LEVEL', [ sensor_response ],
        )

        display_data = EntityStateDisplayData( status_data )

        self.assertEqual( display_data.svg_status_style.status_value, 'off' )

    # Edge Cases and Default Behavior Tests
    
    def test_no_sensor_data_returns_default_style(self):
        """Test default style is returned when no sensor data exists."""
        status_data = self._create_entity_state_status_data('TEMPERATURE', [])
        
        display_data = EntityStateDisplayData(status_data)
        
        # Should use default style with DEFAULT_STATUS_VALUE when no sensor data
        self.assertIsNotNone(display_data.svg_status_style)
        # The style will be created via StatusStyle.default()

    def test_unmapped_entity_type_returns_default_style(self):
        """Test unmapped entity types return default style with sensor value."""
        sensor_response = self._create_mock_sensor_response('25.5')
        status_data = self._create_entity_state_status_data('HUMIDITY', [sensor_response])
        
        with patch.object(StatusStyle, 'default') as mock_default:
            expected_style = Mock()
            mock_default.return_value = expected_style
            
            display_data = EntityStateDisplayData(status_data)
            
            mock_default.assert_called_once_with(status_value='25.5')
            self.assertEqual(display_data.svg_status_style, expected_style)

    def test_single_sensor_value_handles_penultimate_gracefully(self):
        """Test single sensor value doesn't break penultimate access."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.IDLE))
        status_data = self._create_entity_state_status_data('MOVEMENT', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        # Should return idle since no penultimate active state
        self.assertEqual(display_data.svg_status_style, StatusStyle.MovementIdle)
        self.assertIsNone(display_data.penultimate_sensor_value)

    # Property Access Tests
    
    def test_css_class_delegates_to_entity_state(self):
        """Test css_class property delegates to entity_state."""
        status_data = self._create_entity_state_status_data('ON_OFF', [])
        display_data = EntityStateDisplayData(status_data)
        
        # Entity state css_class should be accessible
        css_class = display_data.css_class
        self.assertIsNotNone(css_class)
        self.assertIn('hi-entity-state', css_class)  # Expected format from entity_state

    def test_attribute_dict_returns_style_dict_when_present(self):
        """Test attribute_dict returns style dictionary when style exists."""
        sensor_response = self._create_mock_sensor_response(str(EntityStateValue.ON))
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        # Should return the style's to_dict() result
        attr_dict = display_data.attribute_dict
        self.assertIsInstance(attr_dict, dict)
        self.assertGreater(len(attr_dict), 0)

    def test_attribute_dict_returns_empty_when_no_style(self):
        """Test attribute_dict returns empty dict when no style."""
        sensor_response = self._create_mock_sensor_response('INVALID')
        status_data = self._create_entity_state_status_data('ON_OFF', [sensor_response])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.attribute_dict, {})

    def test_latest_sensor_value_extraction(self):
        """Test latest_sensor_value extracts first response value."""
        response1 = self._create_mock_sensor_response('VALUE1')
        response2 = self._create_mock_sensor_response('VALUE2')
        status_data = self._create_entity_state_status_data('ON_OFF', [response1, response2])
        
        display_data = EntityStateDisplayData(status_data)
        
        self.assertEqual(display_data.latest_sensor_value, 'VALUE1')

    def test_penultimate_sensor_value_extraction(self):
        """Test penultimate_sensor_value extracts second response value."""
        response1 = self._create_mock_sensor_response('VALUE1')
        response2 = self._create_mock_sensor_response('VALUE2')
        status_data = self._create_entity_state_status_data('ON_OFF', [response1, response2])

        display_data = EntityStateDisplayData(status_data)

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
        return EntityStateDisplayData( status_data )

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
        display_data = EntityStateDisplayData( status_data )
        self.assertEqual( display_data.latest_display_label, '' )


class TestRecentStateValueSummary(BaseTestCase):
    """``recent_state_value_summary`` exposes the cached
    SensorResponse list (already deduped by value change in
    ``SensorResponseManager``) as a display-ready structure. Each
    entry's label flows through the same conversion pipeline as
    ``latest_display_label``; the framework adds no completeness
    claims and does not query the DB."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='SENSOR',
        )

    def _make_display_data(self, entity_state_type_str, value_timestamp_pairs,
                           units=None):
        entity_state = EntityState.objects.create(
            entity = self.entity,
            entity_state_type_str = entity_state_type_str,
            units = units,
        )
        responses = []
        for value, ts in value_timestamp_pairs:
            response = Mock(spec=SensorResponse)
            response.value = value
            response.timestamp = ts
            responses.append( response )
        status_data = EntityStateStatusData(
            entity_state = entity_state,
            sensor_response_list = responses,
            controller_data_list = [],
        )
        return EntityStateDisplayData( status_data )

    def test_empty_sensor_response_list_returns_none(self):
        # No cached responses (fresh install, cache cleared, sensor
        # never reported) → caller distinguishes "nothing to show"
        # from a populated-but-old summary without inspecting list
        # length.
        display_data = self._make_display_data( 'MOVEMENT', [] )
        self.assertIsNone( display_data.recent_state_value_summary )

    def test_single_entry_populates_latest_only(self):
        now = datetime.now()
        display_data = self._make_display_data(
            'SMOKE', [ ( str(EntityStateValue.SMOKE_DETECTED), now ) ],
        )
        summary = display_data.recent_state_value_summary
        self.assertIsInstance( summary, RecentStateValueSummary )
        self.assertEqual( len( summary.entries ), 1 )
        self.assertIsNotNone( summary.latest )
        self.assertIsNone( summary.penultimate )
        self.assertEqual( summary.latest.timestamp, now )

    def test_multi_entry_preserves_newest_first_order(self):
        # SensorResponseManager already LPUSHes newest-first; the
        # summary preserves that order so ``latest`` is index [0]
        # and ``penultimate`` is index [1]. Timestamps are
        # timezone-aware because EntityStateDisplayData's status-style
        # computation subtracts against ``datetimeproxy.now()``.
        now = datetimeproxy.now()
        earlier = now - timedelta( minutes = 14 )
        oldest = now - timedelta( hours = 2 )
        display_data = self._make_display_data(
            'SMOKE',
            [
                ( str(EntityStateValue.OFF), now ),
                ( str(EntityStateValue.SMOKE_DETECTED), earlier ),
                ( str(EntityStateValue.OFF), oldest ),
            ],
        )
        summary = display_data.recent_state_value_summary
        self.assertEqual( len( summary.entries ), 3 )
        self.assertEqual( summary.latest.timestamp, now )
        self.assertEqual( summary.penultimate.timestamp, earlier )
        self.assertEqual( summary.entries[2].timestamp, oldest )

    def test_entry_label_matches_latest_display_label_for_enum(self):
        # Per-entry conversion must produce identical labels to the
        # single-entry path so panels render history rows that look
        # like the current value (just at different timestamps).
        display_data = self._make_display_data(
            'SMOKE',
            [ ( str(EntityStateValue.SMOKE_DETECTED), datetime.now() ) ],
        )
        summary = display_data.recent_state_value_summary
        self.assertEqual(
            summary.latest.display_label,
            display_data.latest_display_label,
        )
        self.assertEqual( summary.latest.display_label, 'Smoke Detected' )

    def test_entry_label_applies_unit_conversion(self):
        # A unit-bearing state's history must convert each cached
        # raw value through the same display-unit translation as
        # the current value; otherwise temperature history would
        # show stored °C while the headline number is °F.
        now = datetime.now()
        display_data = self._make_display_data(
            'TEMPERATURE',
            [ ( '22', now ), ( '21', now - timedelta( minutes = 5 ) ) ],
            units = '°C',
        )
        summary = display_data.recent_state_value_summary
        for entry in summary.entries:
            self.assertTrue(
                '°F' in entry.display_label or '°C' in entry.display_label,
                f'expected temperature unit symbol in entry label,'
                f' got {entry.display_label!r}',
            )
        # Latest entry must equal the latest_display_label so panels
        # that show both the headline and the history don't disagree.
        self.assertEqual(
            summary.latest.display_label,
            display_data.latest_display_label,
        )

    def test_summary_is_memoized(self):
        # ``cached_property`` semantics: repeated access returns the
        # same object so panels touching the summary multiple times
        # (e.g. once for latest, once for penultimate) don't pay the
        # per-entry conversion cost on each access.
        display_data = self._make_display_data(
            'SMOKE',
            [ ( str(EntityStateValue.SMOKE_DETECTED), datetime.now() ) ],
        )
        first = display_data.recent_state_value_summary
        second = display_data.recent_state_value_summary
        self.assertIs( first, second )

    def test_state_value_entry_is_immutable_dataclass(self):
        # Frozen dataclass: panels can't mutate per-entry fields
        # mid-render. Documents the immutability contract.
        entry = StateValueEntry(
            display_label = 'x', timestamp = datetime.now(),
        )
        with self.assertRaises( Exception ):
            entry.display_label = 'y'


class TestToPollingUpdateDict(BaseTestCase):
    """``to_polling_update_dict`` builds the per-EntityState row of
    the unified ``entityStateStatusMap``. Pins the contract for
    each kind of EntityState the polling path sees: sensor-only
    (no ``controller``), unit-bearing (``magnitude`` and ``unit``
    present in ``display``), unit-less enum (``magnitude``/``unit``
    absent), the always-present ``display`` key, and the optional
    ``status`` / ``svg_style`` bundle for elements that opt in via
    ``[data-status]`` / ``[data-svg-style]``."""

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
        return EntityStateDisplayData( status_data )

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

    def test_unit_bearing_display_includes_magnitude_and_unit(self):
        display_data = self._make_display_data(
            'TEMPERATURE', '21', units = '°C',
        )
        row = display_data.to_polling_update_dict()
        display = row[ 'display' ]
        self.assertIn( 'text', display )
        self.assertIn( 'magnitude', display )
        self.assertIn( 'unit', display )

    def test_unit_less_display_omits_magnitude_and_unit(self):
        display_data = self._make_display_data(
            'MOVEMENT', str(EntityStateValue.ACTIVE),
        )
        row = display_data.to_polling_update_dict()
        display = row[ 'display' ]
        self.assertIn( 'text', display )
        self.assertNotIn( 'magnitude', display )
        self.assertNotIn( 'unit', display )

    def test_display_text_is_human_readable_label(self):
        # Same source of truth as ``value_label`` template filter —
        # JS sets element.textContent to this string.
        display_data = self._make_display_data(
            'SMOKE', str(EntityStateValue.SMOKE_DETECTED),
        )
        row = display_data.to_polling_update_dict()
        self.assertEqual( row[ 'display' ][ 'text' ], 'Smoke Detected' )

    def test_display_text_humanizes_free_form_wire_value(self):
        # DISCRETE-typed states (HA hvac_action, fan preset, etc.)
        # carry free-form wire values not bound to an
        # EntityStateValue member. The polling map's display text
        # humanizes them so the sensor card displays a readable
        # label on poll refresh — the headline behavior of #310.
        display_data = self._make_display_data( 'DISCRETE', 'heating' )
        row = display_data.to_polling_update_dict()
        self.assertEqual( row[ 'display' ][ 'text' ], 'Heating' )

    def test_status_present_when_svg_style_present(self):
        # SVG-styled states publish both a top-level ``status`` (for
        # ``[data-status]`` consumers like panel roots) and the full
        # ``svg_style`` bundle (for ``[data-svg-style]`` consumers
        # like LocationView icon ``<g>`` elements).
        display_data = self._make_display_data(
            'MOVEMENT', str(EntityStateValue.ACTIVE),
        )
        row = display_data.to_polling_update_dict()
        self.assertIn( 'status', row )
        self.assertIn( 'svg_style', row )
        self.assertEqual( row[ 'status' ], row[ 'svg_style' ][ 'status' ] )

    def test_status_and_svg_style_omitted_when_no_svg_style(self):
        # When the value produces no svg_status_style (e.g., ON_OFF
        # with an unrecognized value), both the top-level status and
        # the svg_style bundle are absent. ``display`` is still
        # present so display-text consumers keep refreshing.
        display_data = self._make_display_data( 'ON_OFF', 'INVALID' )
        row = display_data.to_polling_update_dict()
        self.assertNotIn( 'status', row )
        self.assertNotIn( 'svg_style', row )
        self.assertIn( 'display', row )


class TestTemperatureStatusStyle(BaseTestCase):
    """TEMPERATURE buckets the absolute reading onto a cold→pleasant→hot
    color ramp. The reading is normalized to canonical °C first, so the
    bucket thresholds hold regardless of the EntityState's stored units;
    an unresolvable reading (no/unknown units, non-numeric) falls back to
    the plain numeric status display."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name = 'Test Entity',
            entity_type_str = 'SENSOR',
        )

    def _make_display_data(self, value, units):
        entity_state = EntityState.objects.create(
            entity = self.entity,
            entity_state_type_str = 'TEMPERATURE',
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
        return EntityStateDisplayData( status_data )

    def test_fahrenheit_buckets_span_cold_to_hot(self):
        # °F readings normalize to °C before bucketing; comfortable room
        # temperatures (68-75°F) land in the green "pleasant" band while
        # only outdoor extremes reach the blue/red ends.
        cases = [
            ( '10', StatusStyle.TemperatureCold ),
            ( '45', StatusStyle.TemperatureCool ),
            ( '70', StatusStyle.TemperaturePleasant ),
            ( '85', StatusStyle.TemperatureWarm ),
            ( '95', StatusStyle.TemperatureHot ),
        ]
        for value, expected_style in cases:
            with self.subTest( fahrenheit = value ):
                display_data = self._make_display_data( value, '°F' )
                self.assertEqual( display_data.svg_status_style, expected_style )

    def test_celsius_uses_same_thresholds(self):
        # The same canonical-°C thresholds apply when the state is
        # already stored in °C (no indoor/outdoor distinction needed).
        display_data = self._make_display_data( '21', '°C' )
        self.assertEqual(
            display_data.svg_status_style, StatusStyle.TemperaturePleasant,
        )

    def test_missing_units_falls_back_to_default_style(self):
        # Without units the reading can't be placed on the scale, so the
        # plain numeric status display is used (status == the value text).
        display_data = self._make_display_data( '21', None )
        self.assertEqual( display_data.svg_status_style.status_value, '21' )

    def test_non_numeric_value_falls_back_to_default_style(self):
        display_data = self._make_display_data( 'unavailable', '°F' )
        self.assertEqual(
            display_data.svg_status_style.status_value, 'unavailable',
        )

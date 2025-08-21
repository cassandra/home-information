import logging
from unittest.mock import Mock

from hi.apps.console.transient_models import VideoStreamEntity
from hi.apps.entity.enums import EntityStateType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestVideoStreamEntity(BaseTestCase):

    def test_video_stream_entity_name_camera_suffix_removal(self):
        """Test name property camera suffix removal logic - complex string processing."""
        # Create mock entity
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Test name ending with 'camera' gets suffix removed
        mock_entity.name = 'Kitchen Camera'
        
        video_stream_entity = VideoStreamEntity(
            entity=mock_entity,
            entity_state=mock_entity_state,
            sensor=mock_sensor
        )
        
        self.assertEqual(video_stream_entity.name, 'Kitchen')
        return

    def test_video_stream_entity_name_camera_suffix_case_insensitive(self):
        """Test name property handles case-insensitive camera suffix - edge case handling."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Test different cases of 'camera'
        test_cases = [
            ('Front Door camera', 'Front Door'),
            ('Garage CAMERA', 'Garage'),
            ('Backyard Camera', 'Backyard'),
        ]
        
        for original_name, expected_name in test_cases:
            with self.subTest(original_name=original_name):
                mock_entity.name = original_name
                
                video_stream_entity = VideoStreamEntity(
                    entity=mock_entity,
                    entity_state=mock_entity_state,
                    sensor=mock_sensor
                )
                
                self.assertEqual(video_stream_entity.name, expected_name)
        return

    def test_video_stream_entity_name_no_camera_suffix(self):
        """Test name property when entity name doesn't end with camera - preserves original name."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Test names that don't end with 'camera'
        test_cases = [
            'Security Monitor',
            'Video Stream',
            'Front Door',
            'Camera Setup Tool',  # 'camera' in middle shouldn't be removed
            'cameras',  # plural shouldn't be removed
        ]
        
        for name in test_cases:
            with self.subTest(name=name):
                mock_entity.name = name
                
                video_stream_entity = VideoStreamEntity(
                    entity=mock_entity,
                    entity_state=mock_entity_state,
                    sensor=mock_sensor
                )
                
                self.assertEqual(video_stream_entity.name, name)
        return

    def test_video_stream_entity_name_edge_cases(self):
        """Test name property edge cases - boundary condition handling."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Test edge cases - the implementation only processes names ending with 'camera' (not spaces)
        edge_cases = [
            ('Camera', 'Camera'),  # Just 'Camera' shouldn't be removed entirely
            ('camera', 'camera'),  # Just 'camera' lowercase shouldn't be removed entirely  
            ('Front  Camera', 'Front'),  # Multiple spaces should be stripped after removal
            ('   Patio Camera', 'Patio'),  # Leading spaces preserved, trailing 'camera' removed and stripped
        ]
        
        for original_name, expected_name in edge_cases:
            with self.subTest(original_name=original_name):
                mock_entity.name = original_name
                
                video_stream_entity = VideoStreamEntity(
                    entity=mock_entity,
                    entity_state=mock_entity_state,
                    sensor=mock_sensor
                )
                
                self.assertEqual(video_stream_entity.name, expected_name)
        return

    def test_video_stream_entity_dataclass_properties(self):
        """Test VideoStreamEntity dataclass properties - proper object composition."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        video_stream_entity = VideoStreamEntity(
            entity=mock_entity,
            entity_state=mock_entity_state,
            sensor=mock_sensor
        )
        
        # Should maintain references to all components
        self.assertEqual(video_stream_entity.entity, mock_entity)
        self.assertEqual(video_stream_entity.entity_state, mock_entity_state)
        self.assertEqual(video_stream_entity.sensor, mock_sensor)
        return

    def test_motion_detection_state_with_movement_state(self):
        """Test motion_detection_state property returns MOVEMENT state when it exists."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Create mock movement state
        mock_movement_state = Mock()
        mock_movement_state.entity_state_type = EntityStateType.MOVEMENT
        
        # Create mock non-movement state
        mock_video_state = Mock()
        mock_video_state.entity_state_type = EntityStateType.VIDEO_STREAM
        
        # Setup entity.states.all() to return both states
        mock_entity.states.all.return_value = [mock_video_state, mock_movement_state]
        
        video_stream_entity = VideoStreamEntity(
            entity=mock_entity,
            entity_state=mock_entity_state,
            sensor=mock_sensor
        )
        
        # Should return the movement state
        self.assertEqual(video_stream_entity.motion_detection_state, mock_movement_state)
        return

    def test_motion_detection_state_without_movement_state(self):
        """Test motion_detection_state property returns None when no MOVEMENT state exists."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Create only non-movement states
        mock_video_state = Mock()
        mock_video_state.entity_state_type = EntityStateType.VIDEO_STREAM
        
        mock_on_off_state = Mock()
        mock_on_off_state.entity_state_type = EntityStateType.ON_OFF
        
        # Setup entity.states.all() to return only non-movement states
        mock_entity.states.all.return_value = [mock_video_state, mock_on_off_state]
        
        video_stream_entity = VideoStreamEntity(
            entity=mock_entity,
            entity_state=mock_entity_state,
            sensor=mock_sensor
        )
        
        # Should return None when no movement state exists
        self.assertIsNone(video_stream_entity.motion_detection_state)
        return

    def test_motion_detection_state_with_multiple_movement_states(self):
        """Test motion_detection_state property returns first MOVEMENT state when multiple exist."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Create multiple movement states
        mock_movement_state1 = Mock()
        mock_movement_state1.entity_state_type = EntityStateType.MOVEMENT
        
        mock_movement_state2 = Mock()
        mock_movement_state2.entity_state_type = EntityStateType.MOVEMENT
        
        # Setup entity.states.all() to return multiple movement states
        mock_entity.states.all.return_value = [mock_movement_state1, mock_movement_state2]
        
        video_stream_entity = VideoStreamEntity(
            entity=mock_entity,
            entity_state=mock_entity_state,
            sensor=mock_sensor
        )
        
        # Should return the first movement state
        self.assertEqual(video_stream_entity.motion_detection_state, mock_movement_state1)
        return

    def test_motion_detection_state_with_no_states(self):
        """Test motion_detection_state property returns None when entity has no states."""
        mock_entity = Mock()
        mock_entity_state = Mock()
        mock_sensor = Mock()
        
        # Setup entity.states.all() to return empty list
        mock_entity.states.all.return_value = []
        
        video_stream_entity = VideoStreamEntity(
            entity=mock_entity,
            entity_state=mock_entity_state,
            sensor=mock_sensor
        )
        
        # Should return None when no states exist
        self.assertIsNone(video_stream_entity.motion_detection_state)
        return

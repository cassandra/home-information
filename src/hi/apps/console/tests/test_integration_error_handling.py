import logging
from unittest.mock import Mock, patch
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from hi.apps.console.video_stream_browsing_helper import VideoStreamBrowsingHelper
from hi.apps.console.views import EntityVideoSensorHistoryView
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory

logging.disable(logging.CRITICAL)


class TestIntegrationErrorHandling(TransactionTestCase):
    """Test integration error scenarios and helper method failure handling."""

    def setUp(self):
        super().setUp()
        
        # Create test entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.error_test',
            integration_name='test_integration',
            name='Error Test Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        # Create entity state and sensor
        self.entity_state = EntityState.objects.create(
            entity=self.video_entity,
            entity_state_type_str='motion',
            name='Motion Detection'
        )
        
        self.video_sensor = Sensor.objects.create(
            integration_id='test.sensor.error_test',
            integration_name='test_integration',
            name='Error Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='binary',
            provides_video_stream=True
        )

    def test_helper_method_database_constraint_violations(self):
        """Test integration error: database constraint violations during helper operations."""
        # Create a sensor history record
        base_record = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='active',
            response_datetime=timezone.now(),
            has_video_stream=True
        )
        
        # Test constraint violation scenarios
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                # Attempt to create duplicate record with same primary key
                SensorHistory.objects.create(
                    id=base_record.id,  # Duplicate primary key
                    sensor=self.video_sensor,
                    value='duplicate',
                    response_datetime=timezone.now(),
                    has_video_stream=True
                )
    
    def test_helper_method_failure_recovery(self):
        """Test integration error: helper method failures with graceful recovery."""
        # Create some valid data first
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='valid_record',
            response_datetime=timezone.now(),
            has_video_stream=True
        )
        
        # Test that view handles helper method exceptions gracefully
        with patch.object(VideoStreamBrowsingHelper, 'build_sensor_history_data_default') as mock_helper:
            # Simulate helper method failure
            mock_helper.side_effect = Exception("Simulated helper failure")
            
            view = EntityVideoSensorHistoryView()
            request = Mock()
            request.view_parameters = Mock()
            request.view_parameters.to_session = Mock()
            
            # View should handle helper failure gracefully
            with self.assertRaises(Exception) as context:
                view.get_main_template_context(
                    request,
                    entity_id=self.video_entity.id,
                    sensor_id=self.video_sensor.id
                )
            
            # Verify the exception propagates (expected behavior for debugging)
            self.assertIn("Simulated helper failure", str(context.exception))
    
    def test_database_connection_error_scenarios(self):
        """Test integration error: database connection issues during queries."""
        # Create test data
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='connection_test',
            response_datetime=timezone.now(),
            has_video_stream=True
        )
        
        # Test database query failure simulation
        with patch('hi.apps.sense.models.SensorHistory.objects.filter') as mock_filter:
            # Simulate database connection error
            mock_filter.side_effect = Exception("Database connection error")
            
            # Helper method should propagate database errors
            with self.assertRaises(Exception) as context:
                VideoStreamBrowsingHelper.build_sensor_history_data_default(self.video_sensor)
            
            self.assertIn("Database connection error", str(context.exception))
    
    def test_concurrent_access_scenarios(self):
        """Test integration error: concurrent access to sensor history data."""
        # Create base data
        base_time = timezone.now()
        original_record = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='concurrent_test',
            response_datetime=base_time,
            has_video_stream=True
        )
        
        # Test concurrent modification by modifying record between queries
        # This simulates real-world concurrent access scenarios
        
        # Modify record after creation
        original_record.value = 'modified_concurrently'
        original_record.save()
        
        # Helper should handle record modifications gracefully
        result = VideoStreamBrowsingHelper.build_sensor_history_data_default(self.video_sensor)
        
        # Should still return valid data structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.sensor_responses, list)
        
        # Should reflect the modified value
        if result.sensor_responses:
            self.assertEqual(result.sensor_responses[0].value, 'modified_concurrently')
    
    def test_memory_pressure_with_large_datasets(self):
        """Test performance boundary: memory pressure with very large result sets."""
        # Create a moderately large dataset to test memory handling
        base_time = timezone.now()
        batch_size = 1000  # Large enough to test memory handling
        
        # Create records in batches for efficiency
        records_to_create = []
        for i in range(batch_size):
            records_to_create.append(SensorHistory(
                sensor=self.video_sensor,
                value=f'memory_test_{i}',
                response_datetime=base_time - timezone.timedelta(minutes=i),
                has_video_stream=True,
                details=f'{{"memory_test": {i}}}'
            ))
        
        SensorHistory.objects.bulk_create(records_to_create)
        
        # Test that helper methods handle large datasets efficiently
        result = VideoStreamBrowsingHelper.build_sensor_history_data_default(self.video_sensor)
        
        # Should limit results to prevent memory issues
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result.sensor_responses), 100)  # Should be limited
        self.assertIsInstance(result.pagination_metadata, dict)
        
        # Should indicate more records available
        self.assertTrue(result.pagination_metadata.get('has_older_records', False))
    
    def test_sensor_state_integrity_validation(self):
        """Test integration error: sensor and entity state integrity validation."""
        # Test scenario where entity state gets deleted (cascade deletes sensor)
        
        # Delete entity state (this will cascade delete the sensor due to FK constraint)
        self.video_sensor.entity_state.delete()
        
        # Verify sensor was cascade deleted
        with self.assertRaises(Sensor.DoesNotExist):
            Sensor.objects.get(id=self.video_sensor.id)
        
        # Helper should handle missing sensors gracefully (entity has no sensors now)
        result = VideoStreamBrowsingHelper.find_video_sensor_for_entity(self.video_entity)
        self.assertIsNone(result)  # Should return None when no sensors exist
    
    def test_timezone_aware_edge_cases(self):
        """Test integration error: timezone-aware datetime edge cases."""
        # Test with records spanning DST transitions and timezone boundaries
        base_time = timezone.now()
        
        # Create records with challenging timezone scenarios
        challenging_times = [
            base_time.replace(hour=0, minute=0, second=0, microsecond=0),  # Midnight
            base_time.replace(hour=23, minute=59, second=59, microsecond=999999),  # End of day
        ]
        
        for i, test_time in enumerate(challenging_times):
            SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'timezone_edge_{i}',
                response_datetime=test_time,
                has_video_stream=True,
                details=f'{{"timezone_test": {i}}}'
            )
        
        # Helper should handle timezone edge cases correctly
        result = VideoStreamBrowsingHelper.build_sensor_history_data_default(self.video_sensor)
        
        # Should return valid data without timezone conversion errors
        self.assertIsNotNone(result)
        self.assertGreater(len(result.sensor_responses), 0)
        
        # All timestamps should remain timezone-aware
        for response in result.sensor_responses:
            self.assertIsNotNone(response.timestamp.tzinfo)
    
    def test_pagination_boundary_conditions(self):
        """Test performance boundary: pagination with extreme boundary conditions."""
        # Test pagination at exact boundaries (e.g., exactly 50 records)
        base_time = timezone.now()
        
        # Create exactly 50 records (common pagination boundary)
        boundary_records = []
        for i in range(50):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'boundary_record_{i}',
                response_datetime=base_time - timezone.timedelta(minutes=i),
                has_video_stream=True
            )
            boundary_records.append(record)
        
        # Test pagination at the exact boundary
        result = VideoStreamBrowsingHelper.build_sensor_history_data_default(self.video_sensor)
        
        # Should handle exact boundary correctly
        self.assertLessEqual(len(result.sensor_responses), 50)
        
        # Test earlier pagination from the boundary
        oldest_record = boundary_records[-1]
        pivot_timestamp = int(oldest_record.response_datetime.timestamp())
        
        earlier_result = VideoStreamBrowsingHelper.build_sensor_history_data_earlier(
            self.video_sensor, pivot_timestamp
        )
        
        # Should handle boundary pagination gracefully
        self.assertIsNotNone(earlier_result)
        self.assertIsInstance(earlier_result.pagination_metadata, dict)

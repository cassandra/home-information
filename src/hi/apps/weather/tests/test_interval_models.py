import logging
from datetime import datetime

from hi.apps.weather.interval_models import (
    IntervalDataPoints,
    SourceFieldData,
)
from hi.apps.weather.transient_models import (
    DataPointSource,
    NumericDataPoint,
    TimeInterval,
)
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestIntervalModels(BaseTestCase):
    """Test the supporting interval model classes."""

    def setUp(self):
        """Set up test data."""
        self.test_source = DataPointSource(
            id='test_source',
            label='Test Source',
            abbreviation='TEST',
            priority=1
        )
        
        self.test_interval = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        self.test_data_point = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 30, 0),
            quantity_ave=UnitQuantity(25.0, 'degC')
        )
        return

    def test_interval_data_points_basic_functionality(self):
        """Test IntervalDataPoints dict-like interface."""
        interval_data_points = IntervalDataPoints()
        
        # Test initial state
        self.assertEqual(len(interval_data_points), 0)
        self.assertNotIn(self.test_interval, interval_data_points)
        
        # Test adding data
        interval_data_points[self.test_interval] = self.test_data_point
        self.assertEqual(len(interval_data_points), 1)
        self.assertIn(self.test_interval, interval_data_points)
        self.assertEqual(interval_data_points[self.test_interval], self.test_data_point)
        
        # Test iteration
        keys = list(interval_data_points.keys())
        values = list(interval_data_points.values())
        items = list(interval_data_points.items())
        
        self.assertEqual(keys, [self.test_interval])
        self.assertEqual(values, [self.test_data_point])
        self.assertEqual(items, [(self.test_interval, self.test_data_point)])
        return

    def test_source_field_data_basic_functionality(self):
        """Test SourceFieldData dict-like interface."""
        source_field_data = SourceFieldData()
        
        # Test auto-creation of IntervalDataPoints
        interval_data_points = source_field_data[self.test_source]
        self.assertIsInstance(interval_data_points, IntervalDataPoints)
        
        # Test persistence
        same_interval_data_points = source_field_data[self.test_source]
        self.assertIs(interval_data_points, same_interval_data_points)
        
        # Test contains
        self.assertIn(self.test_source, source_field_data)
        return

    def test_interval_data_points_empty_operations(self):
        """Test IntervalDataPoints operations on empty collection."""
        interval_data_points = IntervalDataPoints()
        
        # Test iteration on empty collection
        self.assertEqual(list(interval_data_points.keys()), [])
        self.assertEqual(list(interval_data_points.values()), [])
        self.assertEqual(list(interval_data_points.items()), [])
        self.assertEqual(list(interval_data_points), [])
        return

    def test_interval_data_points_multiple_intervals(self):
        """Test IntervalDataPoints with multiple intervals."""
        interval_data_points = IntervalDataPoints()
        
        # Create second interval and data point
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 13, 0, 0),
            end=datetime(2024, 1, 1, 14, 0, 0)
        )
        data_point2 = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 13, 30, 0),
            quantity_ave=UnitQuantity(30.0, 'degC')
        )
        
        # Add both intervals
        interval_data_points[self.test_interval] = self.test_data_point
        interval_data_points[interval2] = data_point2
        
        # Test length and membership
        self.assertEqual(len(interval_data_points), 2)
        self.assertIn(self.test_interval, interval_data_points)
        self.assertIn(interval2, interval_data_points)
        
        # Test iteration returns all items
        keys = list(interval_data_points.keys())
        values = list(interval_data_points.values())
        
        self.assertEqual(len(keys), 2)
        self.assertEqual(len(values), 2)
        self.assertIn(self.test_interval, keys)
        self.assertIn(interval2, keys)
        self.assertIn(self.test_data_point, values)
        self.assertIn(data_point2, values)
        return

    def test_source_field_data_multiple_sources(self):
        """Test SourceFieldData with multiple data sources."""
        source_field_data = SourceFieldData()
        
        # Create second source
        source2 = DataPointSource(
            id='test_source_2',
            label='Test Source 2',
            abbreviation='TEST2',
            priority=2
        )
        
        # Access both sources
        intervals1 = source_field_data[self.test_source]
        intervals2 = source_field_data[source2]
        
        # Should be different instances
        self.assertIsNot(intervals1, intervals2)
        
        # Both should be in the source map
        self.assertIn(self.test_source, source_field_data)
        self.assertIn(source2, source_field_data)
        
        # Test iteration
        sources = list(source_field_data.keys())
        interval_maps = list(source_field_data.values())
        
        self.assertEqual(len(sources), 2)
        self.assertEqual(len(interval_maps), 2)
        self.assertIn(self.test_source, sources)
        self.assertIn(source2, sources)
        self.assertIn(intervals1, interval_maps)
        self.assertIn(intervals2, interval_maps)
        return

    def test_source_field_data_direct_assignment(self):
        """Test direct assignment to SourceFieldData."""
        source_field_data = SourceFieldData()
        interval_data_points = IntervalDataPoints()
        
        # Add some data to the interval data points
        interval_data_points[self.test_interval] = self.test_data_point
        
        # Directly assign the interval data points
        source_field_data[self.test_source] = interval_data_points
        
        # Should return the same instance
        retrieved = source_field_data[self.test_source]
        self.assertIs(retrieved, interval_data_points)
        self.assertEqual(len(retrieved), 1)
        self.assertIn(self.test_interval, retrieved)
        return
    

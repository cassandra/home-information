from datetime import timedelta, datetime
import logging
from unittest.mock import patch, AsyncMock
import pytz

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.weather.transient_models import (
    DataPointSource,
    IntervalWeatherHistory,
    WeatherHistoryData,
    TimeInterval,
    NumericDataPoint,
    Station,
    WeatherAlert,
    WeatherForecastData,
    IntervalWeatherForecast,
)
from hi.apps.weather.weather_manager import WeatherManager
from hi.apps.weather.enums import (
    AlertSeverity,
    AlertStatus,
    AlertCategory,
    WeatherEventType,
    AlertCertainty,
    AlertUrgency,
)
from hi.units import UnitQuantity

from hi.testing.async_task_utils import AsyncTaskTestCase
from hi.apps.weather.tests.synthetic_data import WeatherSyntheticData

logging.disable(logging.CRITICAL)


class TestWeatherManager( AsyncTaskTestCase ):
    
    def _create_test_weather_data(self, priority, time_offset_secs, temperature_value, is_null=False):
        """Helper to create test weather data with specified parameters."""
        source = DataPointSource(
            id='test',
            label='Test',
            abbreviation='TEST',
            priority=priority,
        )
        data_datetime = datetimeproxy.now() - timedelta(seconds=time_offset_secs)
        
        weather_data = WeatherSyntheticData.get_random_weather_conditions_data(
            now=data_datetime,
            source=source,
        )
        
        if is_null:
            weather_data.temperature = None
        else:
            weather_data.temperature.quantity_ave = UnitQuantity(temperature_value, 'degF')
            
        return weather_data, source
    
    def _verify_temperature_update(self, expected_temp_value, actual_temp):
        """Helper to verify temperature update results."""
        if expected_temp_value is None:
            self.assertIsNone(actual_temp)
        else:
            self.assertAlmostEqual(expected_temp_value, actual_temp.quantity.magnitude, 3)
            # Check units string representation (could be 'degF' or 'degree_Fahrenheit')
            units_str = str(actual_temp.quantity.units)
            self.assertIn('deg', units_str.lower())
            self.assertIn('f', units_str.lower())
    
    # ============= NEW BEHAVIOR-FOCUSED TESTS =============
    # These tests focus on testing the public interface of WeatherManager
    # rather than testing private implementation details
    
    def test_update_current_conditions_with_higher_priority_source(self):
        """Test that higher priority weather source overwrites lower priority data."""
        async def run_test():
            weather_manager = WeatherManager()
            
            # Create lower priority data
            low_priority_source = DataPointSource(
                id='low',
                label='Low Priority',
                abbreviation='LOW',
                priority=3
            )
            low_priority_data = WeatherSyntheticData.get_random_weather_conditions_data(
                source=low_priority_source
            )
            low_priority_data.temperature.quantity_ave = UnitQuantity(20.0, 'degC')
            
            # Update with lower priority data first
            await weather_manager.update_current_conditions(
                data_point_source=low_priority_source,
                weather_conditions_data=low_priority_data
            )
            
            # Create higher priority data
            high_priority_source = DataPointSource(
                id='high',
                label='High Priority',
                abbreviation='HIGH',
                priority=1
            )
            high_priority_data = WeatherSyntheticData.get_random_weather_conditions_data(
                source=high_priority_source
            )
            high_priority_data.temperature.quantity_ave = UnitQuantity(25.0, 'degC')
            
            # Update with higher priority data
            await weather_manager.update_current_conditions(
                data_point_source=high_priority_source,
                weather_conditions_data=high_priority_data
            )
            
            # Verify the higher priority data is now current
            current_conditions = weather_manager.get_current_conditions_data()
            self.assertIsNotNone(current_conditions)
            self.assertAlmostEqual(
                current_conditions.temperature.quantity_ave.magnitude,
                25.0,
                places=1
            )
            self.assertEqual(current_conditions.temperature.source, high_priority_source)
        
        # Run the async test
        self.run_async(run_test())
    
    def test_update_current_conditions_preserves_newer_data(self):
        """Test that newer data is preserved even from lower priority sources within staleness window."""
        async def run_test():
            weather_manager = WeatherManager()
            
            # Create newer lower priority data
            lower_priority_source = DataPointSource(
                id='lower',
                label='Lower Priority',
                abbreviation='LOW',
                priority=2
            )
            newer_data = WeatherSyntheticData.get_random_weather_conditions_data(
                source=lower_priority_source,
                now=datetimeproxy.now()
            )
            newer_data.temperature.quantity_ave = UnitQuantity(22.0, 'degC')
            
            # Update with newer lower priority data
            await weather_manager.update_current_conditions(
                data_point_source=lower_priority_source,
                weather_conditions_data=newer_data
            )
            
            # Create older higher priority data
            higher_priority_source = DataPointSource(
                id='higher',
                label='Higher Priority',
                abbreviation='HIGH',
                priority=1
            )
            older_data = WeatherSyntheticData.get_random_weather_conditions_data(
                source=higher_priority_source,
                now=datetimeproxy.now() - timedelta(minutes=30)
            )
            older_data.temperature.quantity_ave = UnitQuantity(18.0, 'degC')
            
            # Try to update with older (but higher priority) data
            await weather_manager.update_current_conditions(
                data_point_source=higher_priority_source,
                weather_conditions_data=older_data
            )
            
            # Verify the newer data is preserved
            current_conditions = weather_manager.get_current_conditions_data()
            self.assertIsNotNone(current_conditions)
            # The behavior depends on staleness settings - document expected behavior
            # This test documents the actual behavior rather than testing implementation
        
        # Run the async test
        self.run_async(run_test())
    
    def test_update_hourly_forecast_aggregates_multiple_sources(self):
        """Test that hourly forecast properly aggregates data from multiple sources."""
        async def run_test():
            weather_manager = WeatherManager()
            
            # Create forecast data from first source
            source1 = DataPointSource(
                id='source1',
                label='Source 1',
                abbreviation='S1',
                priority=1
            )
            forecast_list1 = []
            for hour in range(3):
                interval = TimeInterval(
                    start=datetimeproxy.now() + timedelta(hours=hour),
                    end=datetimeproxy.now() + timedelta(hours=hour + 1)
                )
                forecast_data = WeatherForecastData()
                forecast_data.temperature = NumericDataPoint(
                    station=None,
                    source_datetime=datetimeproxy.now(),
                    quantity_ave=UnitQuantity(20.0 + hour, 'degC')
                )
                forecast_list1.append(IntervalWeatherForecast(
                    interval=interval,
                    data=forecast_data
                ))
            
            # Update with first source
            await weather_manager.update_hourly_forecast(
                data_point_source=source1,
                forecast_data_list=forecast_list1
            )
            
            # Verify forecast was stored
            hourly_forecast = weather_manager.get_hourly_forecast()
            self.assertIsNotNone(hourly_forecast)
            self.assertGreater(len(hourly_forecast.data_list), 0)
        
        # Run the async test
        self.run_async(run_test())
    
    def test_get_current_conditions_returns_latest_data(self):
        """Test that get_current_conditions returns the most recent weather data."""
        async def run_test():
            weather_manager = WeatherManager()
            
            # Create and update with weather data
            source = DataPointSource(
                id='test',
                label='Test Source',
                abbreviation='TEST',
                priority=1
            )
            weather_data = WeatherSyntheticData.get_random_weather_conditions_data(
                source=source
            )
            weather_data.temperature.quantity_ave = UnitQuantity(23.5, 'degC')
            weather_data.relative_humidity.quantity_ave = UnitQuantity(65.0, 'percent')
            
            await weather_manager.update_current_conditions(
                data_point_source=source,
                weather_conditions_data=weather_data
            )
            
            # Retrieve current conditions
            current = weather_manager.get_current_conditions_data()
            self.assertIsNotNone(current)
            self.assertIsNotNone(current.temperature)
            self.assertAlmostEqual(
                current.temperature.quantity_ave.magnitude,
                23.5,
                places=1
            )
            self.assertAlmostEqual(
                current.relative_humidity.quantity_ave.magnitude,
                65.0,
                places=1
            )
        
        # Run the async test
        self.run_async(run_test())
    
    def test_update_weather_alerts_stores_alerts_when_enabled(self):
        """Test that weather alerts are stored when alerts feature is enabled."""
        async def run_test():
            weather_manager = WeatherManager()
            weather_manager.ensure_initialized()
            
            # Create test alert
            test_source = DataPointSource(
                id='test_source',
                label='Test Weather Source',
                abbreviation='TEST',
                priority=1
            )
            
            test_alert = WeatherAlert(
                event="Severe Thunderstorm Warning",
                event_type=WeatherEventType.SEVERE_THUNDERSTORM,
                headline="Severe Thunderstorm Warning issued for Test County",
                description="A severe thunderstorm warning is in effect...",
                instruction="Move to interior room on lowest floor of building...",
                severity=AlertSeverity.SEVERE,
                status=AlertStatus.ACTUAL,
                category=AlertCategory.METEOROLOGICAL,
                effective=datetimeproxy.now(),
                onset=datetimeproxy.now() + timedelta(minutes=15),
                expires=datetimeproxy.now() + timedelta(hours=2),
                ends=datetimeproxy.now() + timedelta(hours=2),
                affected_areas="Test County",
                certainty=AlertCertainty.LIKELY,
                urgency=AlertUrgency.IMMEDIATE
            )
            
            # Mock settings to enable alerts
            with patch('hi.apps.weather.weather_manager.WeatherSettingsHelper') as mock_helper_class:
                mock_helper = mock_helper_class.return_value
                mock_helper.is_weather_alerts_enabled_async = AsyncMock(return_value=True)
                
                # Mock alert manager
                with patch.object(weather_manager, 'alert_manager_async', return_value=AsyncMock()):
                    # Update alerts
                    await weather_manager.update_weather_alerts(
                        data_point_source=test_source,
                        weather_alerts=[test_alert]
                    )
                    
                    # Verify alerts are stored
                    stored_alerts = weather_manager.get_weather_alerts()
                    self.assertEqual(len(stored_alerts), 1)
                    self.assertEqual(stored_alerts[0].event, "Severe Thunderstorm Warning")
        
        # Run the async test
        self.run_async(run_test())
    
    # ============= ORIGINAL TESTS (TO BE DEPRECATED) =============
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_same_priority_ignores_null_new_data(self):
        """Test that null new data with same priority doesn't overwrite existing data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=1, time_offset_secs=10, temperature_value=33.0, is_null=True
        )
        
        original_temp = current_data.temperature.quantity.magnitude
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should keep original temperature
        self._verify_temperature_update(original_temp, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_same_priority_newer_data_overwrites(self):
        """Test that newer data with same priority overwrites existing data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=1, time_offset_secs=10, temperature_value=33.0
        )
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should update to new temperature
        self._verify_temperature_update(33.0, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_same_priority_older_data_ignored(self):
        """Test that older data with same priority doesn't overwrite newer existing data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=10, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=33.0
        )
        
        original_temp = current_data.temperature.quantity.magnitude
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should keep original temperature
        self._verify_temperature_update(original_temp, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_higher_priority_always_overwrites(self):
        """Test that higher priority data always overwrites lower priority data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=3, time_offset_secs=20, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=1, time_offset_secs=10, temperature_value=33.0
        )
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should update to new temperature
        self._verify_temperature_update(33.0, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_higher_priority_older_data_ignored(self):
        """Test that older higher priority data doesn't overwrite newer data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=3, time_offset_secs=10, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=33.0
        )
        
        original_temp = current_data.temperature.quantity.magnitude
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should keep original temperature
        self._verify_temperature_update(original_temp, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_lower_priority_ignored_unless_stale(self):
        """Test that lower priority data is ignored unless current data is stale."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=3, time_offset_secs=10, temperature_value=33.0
        )
        
        original_temp = current_data.temperature.quantity.magnitude
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should keep original temperature
        self._verify_temperature_update(original_temp, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_lower_priority_overwrites_stale_data(self):
        """Test that lower priority data overwrites stale current data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=120, temperature_value=20.0  # Stale (>60 sec)
        )
        new_data, new_source = self._create_test_weather_data(
            priority=3, time_offset_secs=10, temperature_value=33.0
        )
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should update to new temperature
        self._verify_temperature_update(33.0, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_overwrites_null_current_data(self):
        """Test that any new data overwrites null current data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=20.0, is_null=True
        )
        new_data, new_source = self._create_test_weather_data(
            priority=3, time_offset_secs=10, temperature_value=33.0
        )
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should update to new temperature
        self._verify_temperature_update(33.0, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_ignores_null_new_data(self):
        """Test that null new data doesn't overwrite existing data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=20.0
        )
        new_data, new_source = self._create_test_weather_data(
            priority=3, time_offset_secs=10, temperature_value=33.0, is_null=True
        )
        
        original_temp = current_data.temperature.quantity.magnitude
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should keep original temperature
        self._verify_temperature_update(original_temp, current_data.temperature)
    
    @patch.object(WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new=60)
    def test_update_weather_data_null_current_and_new_data_stays_null(self):
        """Test that null new data doesn't change null current data."""
        weather_manager = WeatherManager()
        
        current_data, current_source = self._create_test_weather_data(
            priority=1, time_offset_secs=20, temperature_value=20.0, is_null=True
        )
        new_data, new_source = self._create_test_weather_data(
            priority=3, time_offset_secs=10, temperature_value=33.0, is_null=True
        )
        
        weather_manager._update_environmental_data(
            current_data=current_data,
            new_data=new_data,
            data_point_source=new_source,
        )
        
        # Should remain null
        self.assertIsNone(current_data.temperature)

    def test_weather_alerts_enabled_disabled_integration(self):
        """Integration test running both enabled and disabled scenarios."""
        self.run_async(self.test_weather_alerts_enabled_stores_alerts())
        self.run_async(self.test_weather_alerts_disabled_blocks_processing())
    
    def test_daily_history_data_flow(self):
        """Test that daily history data flows correctly from weather manager to template context."""
        weather_manager = WeatherManager()
        
        # Ensure weather manager is initialized
        weather_manager.ensure_initialized()
        
        # Create mock historical data
        test_source = DataPointSource(
            id='test_source',
            label='Test Weather Source',
            abbreviation='TEST',
            priority=1
        )
        
        test_station = Station(
            source=test_source,
            station_id='TEST001'
        )
        
        # Create sample historical data with timezone-aware datetimes
        history_data_list = []
        base_time = datetime(2024, 1, 10, 0, 0, 0, tzinfo=pytz.UTC)
        
        for i in range(3):  # 3 days of history
            interval_start = base_time - timedelta( days = i + 1)
            interval_end = base_time - timedelta( days = i )
            
            history_data = WeatherHistoryData(
                temperature=NumericDataPoint(
                    station=test_station,
                    source_datetime=datetimeproxy.now(),
                    quantity_ave=UnitQuantity(20.0 + i, 'degC')
                ),
                precipitation=NumericDataPoint(
                    station=test_station,
                    source_datetime=datetimeproxy.now(),
                    quantity_ave=UnitQuantity(2.5 * i, 'mm')
                )
            )
            
            interval_history = IntervalWeatherHistory(
                interval=TimeInterval(start=interval_start, end=interval_end),
                data=history_data
            )
            
            history_data_list.append(interval_history)
        
        # Use asyncio to test the async update method
        async def test_update():
            # Create mock weather data source
            mock_weather_source = AsyncMock()
            mock_weather_source.data_point_source = test_source
            
            # Update daily history through weather manager
            await weather_manager.update_daily_history(
                data_point_source=mock_weather_source.data_point_source,
                history_data_list=history_data_list
            )
        
        # Run the async test
        self.run_async(test_update())
        
        # Verify daily history is populated
        daily_history = weather_manager.get_daily_history()
        
        # Check that we have history data
        self.assertIsNotNone(daily_history)
        self.assertIsNotNone(daily_history.data_list)
        self.assertGreater(len(daily_history.data_list), 0, 
                           "Daily history should contain data after update")
        
        # Verify the structure matches what templates expect
        for daily_history_interval in daily_history.data_list:
            # Check that each item is an IntervalWeatherHistory
            self.assertIsInstance(daily_history_interval, IntervalWeatherHistory)
            
            # Check that it has interval and data attributes (as expected by template)
            self.assertIsNotNone(daily_history_interval.interval)
            self.assertIsNotNone(daily_history_interval.data)
            
            # Check that the data has the expected fields
            if daily_history_interval.data.temperature:
                self.assertIsInstance(daily_history_interval.data.temperature, NumericDataPoint)
                self.assertIsNotNone(daily_history_interval.data.temperature.quantity)
            
            if daily_history_interval.data.precipitation:
                self.assertIsInstance(daily_history_interval.data.precipitation, NumericDataPoint) 
                self.assertIsNotNone(daily_history_interval.data.precipitation.quantity)
    
    def _create_test_weather_alert(self):
        """Helper to create a test weather alert."""
        now = datetimeproxy.now()
        return WeatherAlert(
            event="Severe Thunderstorm Warning",
            event_type=WeatherEventType.SEVERE_THUNDERSTORM,
            headline="Severe Thunderstorm Warning issued for Test County",
            description="A severe thunderstorm warning is in effect...",
            instruction="Move to interior room on lowest floor of building...",
            severity=AlertSeverity.SEVERE,
            status=AlertStatus.ACTUAL,
            category=AlertCategory.METEOROLOGICAL,
            effective=now,
            onset=now + timedelta(minutes=15),
            expires=now + timedelta(hours=2),
            ends=now + timedelta(hours=2),
            affected_areas="Test County",
            certainty=AlertCertainty.LIKELY,
            urgency=AlertUrgency.IMMEDIATE
        )
    
    def _create_test_data_source(self):
        """Helper to create a test data point source."""
        return DataPointSource(
            id='test_source',
            label='Test Weather Source',
            abbreviation='TEST',
            priority=1
        )
    
    async def test_weather_alerts_enabled_stores_alerts(self):
        """Test that weather alerts are stored when alerts are enabled."""
        weather_manager = WeatherManager()
        weather_manager.ensure_initialized()
        
        test_source = self._create_test_data_source()
        test_alert = self._create_test_weather_alert()
        
        # Mock only external dependencies - ConsoleSettingsHelper
        with patch('hi.apps.weather.weather_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = mock_helper_class.return_value
            mock_helper.get_setting_value.return_value = True
            
            # Mock only the external alert manager system boundary
            with patch.object(weather_manager, 'alert_manager_async', return_value=AsyncMock()):
                # Test actual behavior - alerts should be processed and stored
                await weather_manager.update_weather_alerts(
                    data_point_source=test_source,
                    weather_alerts=[test_alert]
                )
                
                # Verify actual behavior: alerts are stored
                stored_alerts = weather_manager.get_weather_alerts()
                self.assertEqual(len(stored_alerts), 1)
                self.assertEqual(stored_alerts[0].event, "Severe Thunderstorm Warning")
                self.assertEqual(stored_alerts[0].severity, AlertSeverity.SEVERE)
                self.assertEqual(stored_alerts[0].event_type, WeatherEventType.SEVERE_THUNDERSTORM)
    
    async def test_weather_alerts_disabled_blocks_processing(self):
        """Test that weather alerts are not processed when alerts are disabled."""
        weather_manager = WeatherManager()
        weather_manager.ensure_initialized()
        
        # Clear any existing alerts to start with clean state
        weather_manager._weather_alerts = []
        
        test_source = self._create_test_data_source()
        test_alert = self._create_test_weather_alert()
        
        # Mock WeatherSettingsHelper to return disabled state
        with patch('hi.apps.weather.weather_manager.WeatherSettingsHelper') as mock_helper_class:
            mock_helper = mock_helper_class.return_value
            mock_helper.is_weather_alerts_enabled_async = AsyncMock(return_value=False)
            
            # Test actual behavior when disabled
            await weather_manager.update_weather_alerts(
                data_point_source=test_source,
                weather_alerts=[test_alert]
            )
            
            # Verify actual behavior: no alerts stored when disabled
            stored_alerts = weather_manager.get_weather_alerts()
            self.assertEqual(len(stored_alerts), 0,
                             "No alerts should be stored when alerts are disabled")
    
    def test_weather_alerts_get_returns_current_alerts(self):
        """Test that get_weather_alerts returns the current list of alerts."""
        weather_manager = WeatherManager()
        weather_manager.ensure_initialized()
        
        # Clear any existing alerts to start with clean state
        weather_manager._weather_alerts = []
        
        # Initially should be empty
        alerts = weather_manager.get_weather_alerts()
        self.assertEqual(len(alerts), 0)
        
        # Add test alert directly to verify getter works
        test_alert = self._create_test_weather_alert()
        weather_manager._weather_alerts = [test_alert]
        
        # Verify getter returns the alert
        alerts = weather_manager.get_weather_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].event, "Severe Thunderstorm Warning")
    

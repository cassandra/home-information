"""
Example usage of the enhanced PeriodicMonitor health tracking capabilities.

This file demonstrates how existing monitors can be updated to use the new
health tracking infrastructure implemented in Phase 1 of issue #207.
"""

import asyncio
import logging

from .periodic_monitor import PeriodicMonitor


class ExampleWeatherMonitor(PeriodicMonitor):
    """
    Example of how a weather monitor might use the health tracking features.
    This demonstrates the patterns that existing monitors should follow.
    """

    def __init__(self):
        super().__init__(
            id='weather-monitor',
            interval_secs=300  # 5 minutes
        )
        self._logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the monitor and register API sources."""
        await super().initialize()

        # Register API sources that this monitor depends on
        self.register_api_source(
            source_id='openweathermap',
            source_name='OpenWeatherMap API'
        )
        self.register_api_source(
            source_id='weatherapi',
            source_name='WeatherAPI.com'
        )

        self._logger.info("Weather monitor initialized with API health tracking")

    async def do_work(self):
        """Main monitoring work with health tracking."""
        try:
            # Fetch weather from primary API
            await self._fetch_weather_from_openweathermap()

            # Fetch weather from secondary API
            await self._fetch_weather_from_weatherapi()

            # If we got here successfully, mark monitor as healthy
            self.mark_monitor_healthy("Weather data updated successfully")

        except Exception as e:
            self._logger.exception(f"Weather monitor cycle failed: {e}")
            # The base class will automatically record this error
            raise

    async def _fetch_weather_from_openweathermap(self):
        """Fetch weather data from OpenWeatherMap API with health tracking."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Simulate API call
            await asyncio.sleep(0.1)  # Simulate network request

            # Simulate occasional failures for demonstration
            import random
            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Simulated API timeout")

            # Calculate response time
            response_time = asyncio.get_event_loop().time() - start_time

            # Track successful API call
            self.track_api_call(
                source_id='openweathermap',
                success=True,
                response_time=response_time
            )

            self._logger.debug(f"OpenWeatherMap API call successful ({response_time:.3f}s)")

        except Exception as e:
            # Calculate response time for failed request
            response_time = asyncio.get_event_loop().time() - start_time

            # Track failed API call
            self.track_api_call(
                source_id='openweathermap',
                success=False,
                response_time=response_time,
                error_message=str(e)
            )

            self._logger.warning(f"OpenWeatherMap API call failed: {e}")
            raise

    async def _fetch_weather_from_weatherapi(self):
        """Fetch weather data from WeatherAPI.com with health tracking."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Simulate API call
            await asyncio.sleep(0.05)  # Simulate network request

            # Calculate response time
            response_time = asyncio.get_event_loop().time() - start_time

            # Track successful API call
            self.track_api_call(
                source_id='weatherapi',
                success=True,
                response_time=response_time
            )

            self._logger.debug(f"WeatherAPI call successful ({response_time:.3f}s)")

        except Exception as e:
            # Calculate response time for failed request
            response_time = asyncio.get_event_loop().time() - start_time

            # Track failed API call
            self.track_api_call(
                source_id='weatherapi',
                success=False,
                response_time=response_time,
                error_message=str(e)
            )

            self._logger.warning(f"WeatherAPI call failed: {e}")
            raise

    def get_health_summary(self) -> dict:
        """
        Get a comprehensive health summary for external consumption.
        This demonstrates how monitors can expose health information.
        """
        health = self.health_status
        return {
            'monitor_id': self.id,
            'overall_status': health.status.label,
            'is_healthy': health.is_healthy,
            'is_critical': health.is_critical,
            'last_check': health.last_check,
            'error_message': health.error_message,
            'error_count': health.error_count,
            'heartbeat_age_seconds': health.monitor_heartbeat_age_seconds,
            'api_sources': [
                {
                    'name': api_source.source_name,
                    'status': api_source.status.label,
                    'total_calls': api_source.total_calls,
                    'failure_rate': f"{api_source.failure_rate:.1f}%",
                    'avg_response_time': f"{api_source.average_response_time:.3f}s" if api_source.average_response_time else None,
                    'consecutive_failures': api_source.consecutive_failures,
                    'last_success': api_source.last_success,
                }
                for api_source in health.api_sources
            ]
        }


# Example usage function
async def example_monitor_lifecycle():
    """
    Demonstrate the complete lifecycle of a monitor with health tracking.
    """
    logger = logging.getLogger(__name__)

    # Create and start monitor
    monitor = ExampleWeatherMonitor()

    try:
        # Start the monitor (this would normally run indefinitely)
        task = asyncio.create_task(monitor.start())

        # Let it run for a few cycles
        await asyncio.sleep(2)

        # Check health status
        health_summary = monitor.get_health_summary()
        logger.info(f"Monitor health: {health_summary}")

        # Stop the monitor
        monitor.stop()
        await asyncio.sleep(0.1)

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Final health check
        final_health = monitor.get_health_summary()
        logger.info(f"Final health: {final_health}")

    except Exception as e:
        logger.exception(f"Monitor example failed: {e}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the example
    asyncio.run(example_monitor_lifecycle())

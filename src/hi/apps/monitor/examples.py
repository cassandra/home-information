"""
Examples demonstrating how to use the monitor health status system.

This file shows practical usage patterns for the new monitor health status
business logic including real-world scenarios for different monitor types.
"""

from datetime import timedelta

import hi.apps.common.datetimeproxy as datetimeproxy
from .enums import (
    MonitorHealthStatusType,
    ApiSourceHealthStatusType,
    MonitorHealthAggregationRule,
    MonitorLabelingPattern
)
from .transient_models import MonitorHealthStatus, ApiSourceHealth
from .health_aggregation_service import MonitorHealthAggregationService


def example_weather_monitor_health():
    """
    Example: Weather monitor with multiple API sources.

    Weather monitor uses 4 API sources:
    - OpenWeatherMap API
    - National Weather Service API
    - WeatherBug API
    - Local weather station
    """
    print("=== Weather Monitor Health Example ===")

    # Create monitor health status
    monitor_health = MonitorHealthStatus(
        status=MonitorHealthStatusType.HEALTHY,
        last_check=datetimeproxy.now(),
        monitor_heartbeat=datetimeproxy.now() - timedelta(seconds=15)  # 15 seconds ago
    )

    # Add API sources with different health statuses
    api_sources = [
        ApiSourceHealth(
            source_id="openweathermap",
            source_name=MonitorLabelingPattern.generate_api_source_label("OpenWeatherMap"),
            status=ApiSourceHealthStatusType.HEALTHY,
            total_calls=100,
            total_failures=2,
            consecutive_failures=0,
            average_response_time=1.2,
            last_success=datetimeproxy.now() - timedelta(minutes=2)
        ),
        ApiSourceHealth(
            source_id="nws",
            source_name=MonitorLabelingPattern.generate_api_source_label("National Weather Service"),
            status=ApiSourceHealthStatusType.DEGRADED,
            total_calls=80,
            total_failures=8,
            consecutive_failures=2,
            average_response_time=6.5,
            last_success=datetimeproxy.now() - timedelta(minutes=5)
        ),
        ApiSourceHealth(
            source_id="weatherbug",
            source_name=MonitorLabelingPattern.generate_api_source_label("WeatherBug"),
            status=ApiSourceHealthStatusType.FAILING,
            total_calls=50,
            total_failures=15,
            consecutive_failures=5,
            average_response_time=12.0,
            last_success=datetimeproxy.now() - timedelta(minutes=15)
        ),
        ApiSourceHealth(
            source_id="local_station",
            source_name=MonitorLabelingPattern.generate_api_source_label(
                "Local Weather Station",
                MonitorLabelingPattern.INTERNAL_SERVICE
            ),
            status=ApiSourceHealthStatusType.HEALTHY,
            total_calls=200,
            total_failures=1,
            consecutive_failures=0,
            average_response_time=0.5,
            last_success=datetimeproxy.now() - timedelta(seconds=30)
        )
    ]

    for source in api_sources:
        monitor_health.add_or_update_api_source(source)

    # Calculate overall health using aggregation service
    aggregation_rule = MonitorHealthAggregationRule.default_for_api_count(len(api_sources))
    overall_health = MonitorHealthAggregationService.calculate_overall_monitor_health(
        monitor_health, aggregation_rule
    )

    # Generate summary
    summary = MonitorHealthAggregationService.get_health_summary_message(
        monitor_health, aggregation_rule
    )

    print(f"Monitor ID: {MonitorLabelingPattern.generate_monitor_id('weather')}")
    print(f"Monitor Label: {MonitorLabelingPattern.generate_monitor_label('weather')}")
    print(f"Aggregation Rule: {aggregation_rule.label}")
    print(f"Overall Health: {overall_health.label}")
    print(f"Summary: {summary}")
    print()

    for source in api_sources:
        print(f"  - {source.source_name}: {source.status.label}")
        print(f"    Success Rate: {source.success_rate_percentage:.1f}%")
        print(f"    Avg Response: {source.average_response_time:.1f}s")
        print(f"    Consecutive Failures: {source.consecutive_failures}")
        print()


def example_alert_monitor_health():
    """
    Example: Alert monitor with no external API dependencies.

    Alert monitor only depends on internal processing and heartbeat.
    """
    print("=== Alert Monitor Health Example ===")

    # Create monitor health status for alert monitor
    monitor_health = MonitorHealthStatus(
        status=MonitorHealthStatusType.HEALTHY,
        last_check=datetimeproxy.now(),
        monitor_heartbeat=datetimeproxy.now() - timedelta(seconds=2)  # Very recent
    )

    # No API sources for alert monitor
    aggregation_rule = MonitorHealthAggregationRule.default_for_api_count(0)
    overall_health = MonitorHealthAggregationService.calculate_overall_monitor_health(
        monitor_health, aggregation_rule
    )

    summary = MonitorHealthAggregationService.get_health_summary_message(
        monitor_health, aggregation_rule
    )

    print(f"Monitor ID: {MonitorLabelingPattern.generate_monitor_id('alert')}")
    print(f"Monitor Label: {MonitorLabelingPattern.generate_monitor_label('alert')}")
    print(f"Aggregation Rule: {aggregation_rule.label}")
    print(f"Overall Health: {overall_health.label}")
    print(f"Summary: {summary}")
    print()


def example_zoneminder_monitor_health():
    """
    Example: ZoneMinder integration monitor with single API source.

    ZoneMinder monitor depends on one integration API.
    """
    print("=== ZoneMinder Monitor Health Example ===")

    # Create monitor health status
    monitor_health = MonitorHealthStatus(
        status=MonitorHealthStatusType.WARNING,
        last_check=datetimeproxy.now(),
        monitor_heartbeat=datetimeproxy.now() - timedelta(minutes=2)  # Stale heartbeat
    )

    # Single API source with connection issues
    api_source = ApiSourceHealth(
        source_id="zoneminder_api",
        source_name=MonitorLabelingPattern.generate_api_source_label(
            "ZoneMinder",
            MonitorLabelingPattern.INTERNAL_SERVICE
        ),
        status=ApiSourceHealthStatusType.DEGRADED,
        total_calls=30,
        total_failures=5,
        consecutive_failures=2,
        average_response_time=8.0,
        last_success=datetimeproxy.now() - timedelta(minutes=3)
    )

    monitor_health.add_or_update_api_source(api_source)

    # Calculate health using single-source aggregation
    aggregation_rule = MonitorHealthAggregationRule.default_for_api_count(1)
    overall_health = MonitorHealthAggregationService.calculate_overall_monitor_health(
        monitor_health, aggregation_rule
    )

    summary = MonitorHealthAggregationService.get_health_summary_message(
        monitor_health, aggregation_rule
    )

    print(f"Monitor ID: {MonitorLabelingPattern.generate_monitor_id('zoneminder', MonitorLabelingPattern.INTEGRATION_MONITOR)}")
    print(f"Monitor Label: {MonitorLabelingPattern.generate_monitor_label('zoneminder', MonitorLabelingPattern.INTEGRATION_HEALTH)}")
    print(f"Aggregation Rule: {aggregation_rule.label}")
    print(f"Overall Health: {overall_health.label}")
    print(f"Summary: {summary}")
    print()


def example_api_health_calculation():
    """
    Example: How to calculate API source health from raw metrics.
    """
    print("=== API Health Calculation Examples ===")

    # Example scenarios
    scenarios = [
        {
            "name": "High-performing API",
            "total_requests": 1000,
            "total_failures": 5,
            "consecutive_failures": 0,
            "avg_response_time": 0.8
        },
        {
            "name": "Degraded API (slow responses)",
            "total_requests": 500,
            "total_failures": 25,
            "consecutive_failures": 1,
            "avg_response_time": 7.2
        },
        {
            "name": "Failing API (consecutive failures)",
            "total_requests": 100,
            "total_failures": 15,
            "consecutive_failures": 6,
            "avg_response_time": 15.0
        }
    ]

    for scenario in scenarios:
        status = MonitorHealthAggregationService.calculate_api_source_health(
            total_requests=scenario["total_requests"],
            total_failures=scenario["total_failures"],
            consecutive_failures=scenario["consecutive_failures"],
            avg_response_time=scenario["avg_response_time"]
        )

        success_rate = (
            (scenario["total_requests"] - scenario["total_failures"])
            / scenario["total_requests"]
        ) * 100

        print(f"{scenario['name']}:")
        print(f"  Status: {status.label}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Avg Response: {scenario['avg_response_time']}s")
        print(f"  Consecutive Failures: {scenario['consecutive_failures']}")
        print()


if __name__ == "__main__":
    """Run all examples to demonstrate the monitor health status system."""
    print("Monitor Health Status Business Logic Examples")
    print("=" * 50)
    print()

    example_weather_monitor_health()
    example_alert_monitor_health()
    example_zoneminder_monitor_health()
    example_api_health_calculation()

    print("=" * 50)
    print("Examples complete. This demonstrates the monitor health status")
    print("business logic for different monitor types and scenarios.")

"""
Unit tests for AggregateHealthStatus aggregation logic.
"""
import unittest
from unittest.mock import MagicMock

from hi.apps.system.aggregate_health_status import AggregateHealthStatus
from hi.apps.system.api_health_status import ApiHealthStatus
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.system.enums import (
    HealthStatusType,
    ApiHealthStatusType,
    HealthAggregationRule
)


class TestAggregateHealthStatus(unittest.TestCase):
    """Test cases for AggregateHealthStatus aggregation logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_status = AggregateHealthStatus(
            provider_id="test_provider",
            provider_name="Test Provider",
            status=HealthStatusType.HEALTHY,
            last_check=MagicMock(),
            aggregation_rule=HealthAggregationRule.ALL_SOURCES_HEALTHY
        )

    def _create_api_status(self, name: str, status: ApiHealthStatusType) -> tuple[ProviderInfo, ApiHealthStatus]:
        """Helper to create API status for testing."""
        provider_info = ProviderInfo(
            provider_id=f"api_{name}",
            provider_name=f"API {name}",
            description=f"Test API {name}"
        )
        api_status = ApiHealthStatus(
            provider_id=f"api_{name}",
            provider_name=f"API {name}",
            status=status,
            total_calls=10,
            total_failures=0
        )
        return provider_info, api_status

    def test_no_api_sources_returns_base_status(self):
        """Test that with no API sources, base status is returned."""
        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY)

    def test_all_sources_healthy_rule(self):
        """Test ALL_SOURCES_HEALTHY aggregation rule."""
        self.base_status.aggregation_rule = HealthAggregationRule.ALL_SOURCES_HEALTHY

        # Test: All healthy → HEALTHY
        self.base_status.api_status_map.clear()
        for i, status in enumerate([ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY]):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY)

        # Test: 3 healthy + 1 disabled → HEALTHY (disabled should be excluded)
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DISABLED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY, "3 healthy + 1 disabled should be HEALTHY")

        # Test: Has failing → ERROR
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.FAILING]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.ERROR)

        # Test: Has unavailable → ERROR
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.UNAVAILABLE]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.ERROR)

        # Test: Has degraded → WARNING
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DEGRADED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.WARNING)

        # Test: Has unknown → WARNING
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.UNKNOWN]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.WARNING)

    def test_majority_sources_healthy_rule(self):
        """Test MAJORITY_SOURCES_HEALTHY aggregation rule."""
        self.base_status.aggregation_rule = HealthAggregationRule.MAJORITY_SOURCES_HEALTHY

        # Test: 3 healthy out of 4 → HEALTHY
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DEGRADED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY)

        # Test: 2 healthy out of 4 → WARNING (not majority)
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DEGRADED, ApiHealthStatusType.DEGRADED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.WARNING)

        # Test: 2 healthy + 1 disabled out of 3 total → HEALTHY (disabled excluded, 2 > 1)
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DISABLED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY, "2 healthy + 1 disabled should be HEALTHY")

    def test_any_source_healthy_rule(self):
        """Test ANY_SOURCE_HEALTHY aggregation rule."""
        self.base_status.aggregation_rule = HealthAggregationRule.ANY_SOURCE_HEALTHY

        # Test: 1 healthy + 3 degraded → HEALTHY
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DEGRADED, ApiHealthStatusType.DEGRADED, ApiHealthStatusType.DEGRADED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY)

        # Test: 1 healthy + 1 disabled → HEALTHY
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DISABLED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY, "1 healthy + 1 disabled should be HEALTHY")

        # Test: Only degraded (no healthy) → WARNING
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.DEGRADED, ApiHealthStatusType.DEGRADED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.WARNING)

    def test_all_sources_disabled(self):
        """Test that when all sources are disabled, base status is used."""
        self.base_status.api_status_map.clear()
        statuses = [ApiHealthStatusType.DISABLED, ApiHealthStatusType.DISABLED]
        for i, status in enumerate(statuses):
            info, api_status = self._create_api_status(f"source{i}", status)
            self.base_status.api_status_map[info] = api_status

        # Should return base status since all API sources are disabled
        result = self.base_status.aggregate_health()
        self.assertEqual(result, HealthStatusType.HEALTHY)

    def test_base_status_and_api_aggregation_combine(self):
        """Test that base status and API aggregation combine correctly using worst status."""
        # Set base status to WARNING
        self.base_status.status = HealthStatusType.WARNING

        # Add all healthy API sources
        self.base_status.api_status_map.clear()
        for i in range(3):
            info, api_status = self._create_api_status(f"source{i}", ApiHealthStatusType.HEALTHY)
            self.base_status.api_status_map[info] = api_status

        # Even though all APIs are healthy, overall should be WARNING due to base status
        result = self.base_status.status
        self.assertEqual(result, HealthStatusType.WARNING, "Base WARNING should override API HEALTHY")

        # Now set base status to ERROR
        self.base_status.status = HealthStatusType.ERROR
        result = self.base_status.status
        self.assertEqual(result, HealthStatusType.ERROR, "Base ERROR should be worst status")

        # Set base status to HEALTHY with one API FAILING
        self.base_status.status = HealthStatusType.HEALTHY
        self.base_status.api_status_map.clear()
        info1, api_status1 = self._create_api_status("source1", ApiHealthStatusType.HEALTHY)
        info2, api_status2 = self._create_api_status("source2", ApiHealthStatusType.FAILING)
        self.base_status.api_status_map[info1] = api_status1
        self.base_status.api_status_map[info2] = api_status2

        result = self.base_status.status
        self.assertEqual(result, HealthStatusType.ERROR, "API FAILING should override base HEALTHY")

    def test_disabled_sources_excluded(self):
        """Test comprehensive scenarios where DISABLED sources are properly excluded."""
        test_cases = [
            # (statuses, rule, expected, description)
            ([ApiHealthStatusType.HEALTHY, ApiHealthStatusType.DISABLED],
             HealthAggregationRule.ALL_SOURCES_HEALTHY, HealthStatusType.HEALTHY,
             "1 healthy + 1 disabled with ALL_SOURCES_HEALTHY"),

            ([ApiHealthStatusType.DEGRADED, ApiHealthStatusType.DISABLED],
             HealthAggregationRule.ALL_SOURCES_HEALTHY, HealthStatusType.WARNING,
             "1 degraded + 1 disabled with ALL_SOURCES_HEALTHY"),

            ([ApiHealthStatusType.FAILING, ApiHealthStatusType.DISABLED],
             HealthAggregationRule.ALL_SOURCES_HEALTHY, HealthStatusType.ERROR,
             "1 failing + 1 disabled with ALL_SOURCES_HEALTHY"),
        ]

        for statuses, rule, expected, description in test_cases:
            with self.subTest(description=description):
                self.base_status.aggregation_rule = rule
                self.base_status.api_status_map.clear()

                for i, status in enumerate(statuses):
                    info, api_status = self._create_api_status(f"source{i}", status)
                    self.base_status.api_status_map[info] = api_status

                result = self.base_status.aggregate_health()
                self.assertEqual(result, expected, f"Failed for: {description}")


if __name__ == '__main__':
    unittest.main()
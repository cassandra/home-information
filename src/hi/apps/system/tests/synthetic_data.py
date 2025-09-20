"""
Synthetic data generation for system health status testing.

This module provides a class to generate realistic test data for health status
scenarios, supporting both regular HealthStatus and ApiHealthAggregator objects.
"""

from datetime import datetime, timedelta
from typing import Dict

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.system.api_health import ApiHealthStatus
from hi.apps.system.api_health_aggregator import ApiHealthAggregator
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.system.enums import (
    HealthStatusType,
    ApiHealthStatusType,
    HealthAggregationRule
)
from hi.apps.system.health_status import HealthStatus


class SystemSyntheticData:
    """
    Generator for synthetic system health status data for testing purposes.

    Provides methods to create realistic HealthStatus and ApiHealthAggregator
    objects with appropriate test data for all status types.
    """

    @classmethod
    def create_health_status_for_testing(cls, status_type: str, has_api_sources: bool):
        """
        Create synthetic health status data for UI testing.

        Args:
            status_type: One of 'unknown', 'healthy', 'warning', 'error', 'disabled'
            has_api_sources: Whether to create ApiHealthAggregator (True) or HealthStatus (False)

        Returns:
            HealthStatus or ApiHealthAggregator instance with appropriate test data
        """
        now = datetimeproxy.now()

        # Map status types to HealthStatusType enums
        status_map = {
            'unknown': HealthStatusType.UNKNOWN,
            'healthy': HealthStatusType.HEALTHY,
            'warning': HealthStatusType.WARNING,
            'error': HealthStatusType.ERROR,
            'disabled': HealthStatusType.DISABLED,
        }

        status_enum = status_map.get(status_type, HealthStatusType.HEALTHY)

        # Base health status data
        base_data = {
            'status': status_enum,
            'last_check': now,
        }

        # Customize data based on status type
        if status_type == 'unknown':
            base_data.update({
                'heartbeat': None,
                'error_message': "No health data available - service not yet initialized",
            })
        elif status_type == 'healthy':
            base_data.update({
                'heartbeat': now,
            })
        elif status_type == 'warning':
            base_data.update({
                'heartbeat': now - timedelta(minutes=2),
                'error_message': "Temporary issue: Service experiencing intermittent connectivity issues",
                'error_count': 3,
            })
        elif status_type == 'error':
            base_data.update({
                'heartbeat': now - timedelta(hours=1),
                'error_message': "Critical error: Service has stopped responding - manual intervention required",
                'error_count': 8,
            })
        elif status_type == 'disabled':
            base_data.update({
                'heartbeat': now,
                'error_message': "Service has been manually disabled for scheduled maintenance",
            })

        if has_api_sources:
            # Create ApiHealthAggregator with sample API sources
            api_sources = cls._create_sample_api_sources(status_type, now)
            aggregation_rule = cls._get_aggregation_rule_for_status(status_type)

            return ApiHealthAggregator(
                api_sources=api_sources,
                aggregation_rule=aggregation_rule,
                **base_data
            )
        else:
            # Create regular HealthStatus
            return HealthStatus(**base_data)

    @classmethod
    def get_status_label(cls, status_type: str) -> str:
        """Get display label for status type."""
        labels = {
            'unknown': 'Unknown Status',
            'healthy': 'Healthy Status',
            'warning': 'Warning Status',
            'error': 'Error Status',
            'disabled': 'Disabled Status',
        }
        return labels.get(status_type, 'Health Status')

    @classmethod
    def _create_sample_api_sources(cls, status_type: str, now: datetime) -> Dict[ProviderInfo, ApiHealthStatus]:
        """Create sample API sources based on status type."""
        if status_type == 'healthy':
            return {
                ProviderInfo(service_name="Primary API", service_id="primary_api"): ApiHealthStatus(
                    service_name="Primary API",
                    service_id="primary_api",
                    status=ApiHealthStatusType.HEALTHY,
                    last_success=now,
                    total_calls=1247,
                    total_failures=5,
                    consecutive_failures=0,
                    average_response_time=0.23,
                    last_response_time=0.21
                ),
                ProviderInfo(service_name="Secondary API", service_id="secondary_api"): ApiHealthStatus(
                    service_name="Secondary API",
                    service_id="secondary_api",
                    status=ApiHealthStatusType.HEALTHY,
                    last_success=now - timedelta(seconds=10),
                    total_calls=892,
                    total_failures=3,
                    consecutive_failures=0,
                    average_response_time=0.45,
                    last_response_time=0.38
                )
            }

        elif status_type == 'warning':
            return {
                ProviderInfo(service_name="Primary API", service_id="primary_api"): ApiHealthStatus(
                    service_name="Primary API",
                    service_id="primary_api",
                    status=ApiHealthStatusType.HEALTHY,
                    last_success=now,
                    total_calls=1247,
                    total_failures=15,
                    consecutive_failures=0,
                    average_response_time=0.23,
                    last_response_time=0.21
                ),
                ProviderInfo(service_name="Secondary API", service_id="secondary_api"): ApiHealthStatus(
                    service_name="Secondary API",
                    service_id="secondary_api",
                    status=ApiHealthStatusType.DEGRADED,
                    last_success=now - timedelta(minutes=3),
                    total_calls=892,
                    total_failures=67,
                    consecutive_failures=2,
                    average_response_time=1.45,
                    last_response_time=2.31
                ),
                ProviderInfo(service_name="Backup API", service_id="backup_api"): ApiHealthStatus(
                    service_name="Backup API",
                    service_id="backup_api",
                    status=ApiHealthStatusType.HEALTHY,
                    last_success=now - timedelta(seconds=30),
                    total_calls=456,
                    total_failures=8,
                    consecutive_failures=0,
                    average_response_time=0.67,
                    last_response_time=0.52
                )
            }

        elif status_type == 'error':
            return {
                ProviderInfo(service_name="Primary API", service_id="primary_api"): ApiHealthStatus(
                    service_name="Primary API",
                    service_id="primary_api",
                    status=ApiHealthStatusType.FAILING,
                    last_success=now - timedelta(hours=2),
                    total_calls=1247,
                    total_failures=425,
                    consecutive_failures=15,
                    average_response_time=5.23,
                    last_response_time=None
                ),
                ProviderInfo(service_name="Secondary API", service_id="secondary_api"): ApiHealthStatus(
                    service_name="Secondary API",
                    service_id="secondary_api",
                    status=ApiHealthStatusType.UNAVAILABLE,
                    last_success=now - timedelta(hours=6),
                    total_calls=892,
                    total_failures=289,
                    consecutive_failures=25,
                    average_response_time=None,
                    last_response_time=None
                )
            }

        elif status_type == 'disabled':
            return {
                ProviderInfo(service_name="Maintenance API", service_id="maintenance_api"): ApiHealthStatus(
                    service_name="Maintenance API",
                    service_id="maintenance_api",
                    status=ApiHealthStatusType.HEALTHY,
                    last_success=now,
                    total_calls=45,
                    total_failures=0,
                    consecutive_failures=0,
                    average_response_time=0.15,
                    last_response_time=0.12
                )
            }

        else:  # unknown
            return {
                ProviderInfo(service_name="Unknown API", service_id="unknown_api"): ApiHealthStatus(
                    service_name="Unknown API",
                    service_id="unknown_api",
                    status=ApiHealthStatusType.UNKNOWN,
                    last_success=None,
                    total_calls=0,
                    total_failures=0,
                    consecutive_failures=0,
                    average_response_time=None,
                    last_response_time=None
                )
            }

    @classmethod
    def _get_aggregation_rule_for_status(cls, status_type: str) -> HealthAggregationRule:
        """Get appropriate aggregation rule based on status type."""
        if status_type == 'error':
            return HealthAggregationRule.ANY_SOURCE_HEALTHY
        elif status_type == 'warning':
            return HealthAggregationRule.MAJORITY_SOURCES_HEALTHY
        else:
            return HealthAggregationRule.ALL_SOURCES_HEALTHY

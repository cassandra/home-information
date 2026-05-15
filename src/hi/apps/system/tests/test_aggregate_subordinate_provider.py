"""
Tests for the subordinate-HealthStatusProvider registration path on
AggregateHealthProvider. The aggregator pulls the subordinate's status
on each read of self.health_status — so a successful base-status update
on the aggregator cannot mask a subordinate that is still reporting a
worse status.
"""
import logging

from django.test import SimpleTestCase

from hi.apps.system.aggregate_health_provider import AggregateHealthProvider
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo

logging.disable(logging.CRITICAL)


class _Aggregator(AggregateHealthProvider):
    @classmethod
    def get_provider_info(cls):
        return ProviderInfo(
            provider_id='test.aggregator',
            provider_name='Test Aggregator',
            description='',
        )


class _Subordinate(HealthStatusProvider):
    def __init__(self, provider_id):
        self._test_provider_id = provider_id
        super().__init__()

    def get_provider_info(self):
        return ProviderInfo(
            provider_id=self._test_provider_id,
            provider_name=self._test_provider_id,
            description='',
        )


class AggregateSubordinateProviderTest(SimpleTestCase):

    def test_subordinate_status_pulled_on_each_health_read(self):
        agg = _Aggregator()
        sub = _Subordinate('test.sub')

        # Establish a healthy baseline on the aggregator.
        agg.update_health_status(HealthStatusType.HEALTHY, 'Reloaded')
        self.assertEqual(agg.health_status.status, HealthStatusType.HEALTHY)

        # Register the subordinate. UNKNOWN doesn't drag the overall
        # status down (it represents "no data," not "bad"), so aggregator
        # remains HEALTHY.
        agg.add_subordinate_health_status_provider(sub)
        self.assertEqual(agg.health_status.status, HealthStatusType.HEALTHY)

        # Subordinate moves to HEALTHY → aggregator still HEALTHY.
        sub.update_health_status(HealthStatusType.HEALTHY, 'init')
        self.assertEqual(agg.health_status.status, HealthStatusType.HEALTHY)

        # Subordinate flips to ERROR.
        sub.update_health_status(HealthStatusType.ERROR, 'broken')
        self.assertEqual(agg.health_status.status, HealthStatusType.ERROR)

        # Aggregator records its OWN healthy state again (e.g.,
        # successful reload). Subordinate is still ERROR; aggregator
        # must still report ERROR. This is the aliasing case the new
        # slot was added to solve.
        agg.update_health_status(HealthStatusType.HEALTHY, 'Reloaded again')
        self.assertEqual(agg.health_status.status, HealthStatusType.ERROR)

        # Only when the subordinate also recovers does the aggregator
        # go HEALTHY.
        sub.update_health_status(HealthStatusType.HEALTHY, 'recovered')
        self.assertEqual(agg.health_status.status, HealthStatusType.HEALTHY)

    def test_remove_subordinate_stops_contribution(self):
        agg = _Aggregator()
        sub = _Subordinate('test.sub')
        agg.update_health_status(HealthStatusType.HEALTHY, 'init')

        agg.add_subordinate_health_status_provider(sub)
        sub.update_health_status(HealthStatusType.ERROR, 'broken')
        self.assertEqual(agg.health_status.status, HealthStatusType.ERROR)

        agg.remove_subordinate_health_status_provider(sub)
        # Aggregator returns to its own base status — subordinate no
        # longer counted.
        self.assertEqual(agg.health_status.status, HealthStatusType.HEALTHY)

    def test_double_registration_is_idempotent(self):
        agg = _Aggregator()
        sub = _Subordinate('test.sub')

        agg.add_subordinate_health_status_provider(sub)
        agg.add_subordinate_health_status_provider(sub)
        self.assertEqual(len(agg._subordinate_health_status_providers), 1)

import copy
import logging
from typing import Sequence

import hi.apps.common.datetimeproxy as datetimeproxy

from .aggregate_health_status import AggregateHealthStatus
from .api_health_status_provider import ApiHealthStatusProvider
from .health_status import HealthStatus
from .health_status_provider import HealthStatusProvider
from .enums import HealthStatusType, HealthAggregationRule

logger = logging.getLogger(__name__)


class AggregateHealthProvider( HealthStatusProvider ):
    """
    Provider for components that aggregate API health from one or more sources.
    Provides health status tracking with API health aggregation capability.

    This provider can be used alongside ApiHealthStatusProvider for components that both
    make their own API calls and need to track/aggregate API health.
    """

    @property
    def initial_health_status(self) -> HealthStatus:
        provider_info = self.get_provider_info()
        return AggregateHealthStatus(
            provider_id = provider_info.provider_id,
            provider_name = provider_info.provider_name,
            status = HealthStatusType.UNKNOWN,
            last_update = datetimeproxy.now(),
            last_message = 'Initialization',
            aggregation_rule = self._get_aggregation_rule()
        )
    
    def _ensure_health_status_provider_setup(self):
        if hasattr( self, '_health_status' ):
            return
        super()._ensure_health_status_provider_setup()
        self._api_health_status_providers = []  # Track API health status providers
        self._subordinate_health_status_providers = []  # Track subordinate HealthStatusProvider sources
        return

    @property
    def health_status(self) -> AggregateHealthStatus:
        """Get aggregated health status (thread-safe, always fresh).

        Subordinate registration must form a DAG. If a subordinate is
        itself an AggregateHealthProvider whose subordinate set
        transitively contains this aggregator, the cyclic refresh
        below would recurse — and because each level reads its
        subordinates outside its own lock, a cycle would manifest as
        infinite recursion rather than deadlock. Today all subordinate
        registrations are leaves (monitors → managers); preserve that
        invariant when adding new subordinate types.
        """
        self._ensure_health_status_provider_setup()
        # Snapshot the registered source lists under our lock, then
        # release before pulling each source's status. Reading another
        # provider's health_status may acquire that provider's lock; if
        # we held our own lock during those reads, a transitive
        # subordinate-of-subordinate aggregator could deadlock against
        # an unrelated lock-acquisition order. Snapshot-and-release
        # avoids the lock-ordering question entirely.
        with self._health_lock:
            api_providers = list( self._api_health_status_providers )
            subordinate_providers = list( self._subordinate_health_status_providers )

        api_snapshots = [
            (p.get_api_provider_info(), p.api_health_status)
            for p in api_providers
        ]
        subordinate_snapshots = [
            (p.get_provider_info(), p.health_status)
            for p in subordinate_providers
        ]

        with self._health_lock:
            self._health_status.api_status_map.clear()
            for provider_info, api_health_status in api_snapshots:
                self._health_status.api_status_map[provider_info] = api_health_status

            self._health_status.subordinate_status_map.clear()
            for provider_info, subordinate_health_status in subordinate_snapshots:
                self._health_status.subordinate_status_map[provider_info] = (
                    subordinate_health_status
                )

            return copy.deepcopy(self._health_status)

    def refresh_aggregated_health(self) -> None:
        # Public refresh — preserved for any external callers, though
        # health_status now refreshes on every read. Implemented in
        # terms of health_status to share the lock-ordering discipline.
        _ = self.health_status
        return

    def _get_aggregation_rule(self) -> HealthAggregationRule:
        """Override to provide custom aggregation rule."""
        return HealthAggregationRule.ALL_SOURCES_HEALTHY
    
    def add_api_health_status_provider(
            self,
            api_health_status_provider : ApiHealthStatusProvider ) -> None:
        """Add an API health status provider to be tracked and aggregated.

        Registration changes are picked up on the next health_status
        read; no eager refresh inside the lock (which would force us
        to read other providers' health_status while holding our own
        lock — see health_status() for the lock-ordering rationale).
        """
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            if api_health_status_provider not in self._api_health_status_providers:
                self._api_health_status_providers.append( api_health_status_provider )
        return

    def add_api_health_status_provider_multi(
            self,
            api_health_status_provider_sequence : Sequence[ ApiHealthStatusProvider ]
    ) -> None:
        """Add API health status providers to be tracked and aggregated."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            for api_health_status_provider in api_health_status_provider_sequence:
                if api_health_status_provider not in self._api_health_status_providers:
                    self._api_health_status_providers.append(api_health_status_provider)
                continue
        return

    def remove_api_health_status_provider(
            self,
            api_health_status_provider : ApiHealthStatusProvider
    ) -> None:
        """Remove an API health status provider from tracking."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            if api_health_status_provider in self._api_health_status_providers:
                self._api_health_status_providers.remove(api_health_status_provider)
        return

    def add_subordinate_health_status_provider(
            self,
            subordinate : HealthStatusProvider ) -> None:
        """
        Register a subordinate HealthStatusProvider whose status
        contributes to this aggregator's overall status. The aggregator
        pulls the subordinate's current status on each read of
        self.health_status — mirroring how add_api_health_status_provider
        treats its providers.

        Use this for non-API sources that should not alias the parent's
        own _base_status: e.g., a polling monitor that watches the same
        subsystem the manager configures. A successful manager reload
        setting _base_status=HEALTHY must not silently overwrite a
        monitor still reporting ERROR — separate slots prevent that.

        Subordinate registration must form a DAG; see health_status().
        """
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            if subordinate not in self._subordinate_health_status_providers:
                self._subordinate_health_status_providers.append( subordinate )
        return

    def remove_subordinate_health_status_provider(
            self,
            subordinate : HealthStatusProvider ) -> None:
        """Remove a subordinate HealthStatusProvider from tracking."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            if subordinate in self._subordinate_health_status_providers:
                self._subordinate_health_status_providers.remove( subordinate )
        return

"""
Framework-level periodic monitor for the Issue #283 sync-check
feature.

A single ``IntegrationSyncCheckMonitor`` runs at a long cadence
(``IntegrationSyncCheck.INTERVAL_SECS``, currently 4 hours), iterates
the enabled and unpaused integrations, gets each integration's
synchronizer via ``gateway.get_synchronizer()``, and dispatches to
its ``check_needs_sync()``. Sync-check rides on the same opt-in
surface as full sync — an integration without a synchronizer
naturally opts out of the periodic drift check too. Per-integration
calls are wrapped in try/except so one integration's transient
failure does not abort the cycle for the others. Sequential (not
parallel) iteration is deliberate: we hit one upstream at a time
across all integrations, which avoids lock-step CPU bursts when
monitors of multiple integrations would otherwise align at the long
boundary.

Lifecycle: started from ``IntegrationManager`` after the
per-integration health monitors have been launched. Stopped from the
same lifecycle. The first cycle runs immediately on start (the base
``PeriodicMonitor`` semantics) — that gives best-effort cache
population at server boot. Per-integration calls that fail because
their underlying manager / client is not yet ready are reported as
errors for this cycle only and the next cycle catches them.
"""

import logging

from hi.apps.alert.enums import AlarmLevel
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .integration_data import IntegrationData
from .sync_check import IntegrationSyncCheck, SyncCheckOutcome

logger = logging.getLogger(__name__)


class IntegrationSyncCheckMonitor( PeriodicMonitor ):

    MONITOR_ID = 'hi.integrations.sync_check_monitor'
    INTERVAL_SECS = IntegrationSyncCheck.INTERVAL_SECS

    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.INTERVAL_SECS,
        )
        return

    def alarm_ceiling(self):
        # Drift detection is informational by design — the user always
        # confirms the actual sync. Cap at INFO so probe failures
        # never escalate beyond a notice.
        return AlarmLevel.INFO

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Integration Sync-Check Monitor',
            description = (
                'Periodic check across integrations for '
                'changes that would warrant a Refresh.'
            ),
            expected_heartbeat_interval_secs = cls.INTERVAL_SECS,
        )

    async def do_work(self):
        # Imported here to avoid an import cycle: IntegrationManager
        # imports this module to start the monitor on init.
        from .integration_manager import IntegrationManager

        manager = IntegrationManager()
        integration_data_list = manager.get_integration_data_list( enabled_only = True )

        outcome_counts = { outcome: 0 for outcome in SyncCheckOutcome }

        for integration_data in integration_data_list:
            if integration_data.is_paused:
                continue
            outcome = await self._check_one_integration( integration_data )
            outcome_counts[ outcome ] += 1
            continue

        self._record_cycle_health( outcome_counts )
        return

    async def _check_one_integration(
            self,
            integration_data : IntegrationData ) -> SyncCheckOutcome:
        """
        Run the per-integration probe and write the result to the
        cache. Sync-check rides on the same opt-in surface as full
        sync: an integration with no synchronizer
        (``gateway.get_synchronizer() is None``) does not participate.
        Any exception from the synchronizer's check is caught here so
        a single integration cannot abort the cycle.
        """
        integration_id = integration_data.integration_id
        gateway = integration_data.integration_gateway

        synchronizer = gateway.get_synchronizer()
        if synchronizer is None:
            # No synchronizer means no sync support — and therefore
            # no sync-check. Cache state is not touched.
            return SyncCheckOutcome.OPTED_OUT

        try:
            delta = await synchronizer.check_needs_sync()
        except Exception as e:
            logger.warning(
                f'Sync check failed for {integration_id}: {e}',
                exc_info = True,
            )
            return SyncCheckOutcome.ERROR

        if delta is None:
            # Synchronizer exists but opted out of sync-check (the
            # default base-class behavior). Cache state is not
            # touched.
            return SyncCheckOutcome.OPTED_OUT

        result = IntegrationSyncCheck.build_result(
            delta = delta,
            integration_label = integration_data.integration_metadata.label,
        )
        IntegrationSyncCheck.set_state(
            integration_id = integration_id,
            result = result,
        )
        return (
            SyncCheckOutcome.NEEDS_SYNC
            if result.needs_sync
            else SyncCheckOutcome.IN_SYNC
        )

    def _record_cycle_health( self,
                              outcome_counts : dict,
                              ) -> None:
        """Summarize the cycle into the monitor's own health-status
        surface. The framework monitor's job is "did I iterate and
        dispatch every enabled integration?" — that always succeeds
        when we reach this method (per-integration call failures are
        absorbed by ``_check_one_integration``'s try/except). So
        cycle outcome is reported as HEALTHY regardless of how many
        individual integration probes errored.

        Per-integration upstream errors are owned by each
        integration's own health monitor (which polls the same
        upstream); duplicating an alert here would just repeat the
        same signal. The error count is still surfaced in the
        message for operator visibility, but it does not escalate
        this monitor's status.

        True framework / process failures (cache layer unavailable,
        ``IntegrationManager`` not initialized, etc.) raise out of
        ``do_work`` and are caught by the base class's
        ``run_query``, which records them as ERROR — that is the
        only path that should alert from this monitor.
        """
        checked = (
            outcome_counts[ SyncCheckOutcome.IN_SYNC ]
            + outcome_counts[ SyncCheckOutcome.NEEDS_SYNC ]
        )
        needs_sync = outcome_counts[ SyncCheckOutcome.NEEDS_SYNC ]
        errors = outcome_counts[ SyncCheckOutcome.ERROR ]

        message = (
            f'Sync check completed: {checked} integration(s) checked, '
            f'{needs_sync} need sync.'
        )
        if errors:
            message += (
                f' ({errors} integration probe error(s) — see '
                f'per-integration health.)'
            )
        self.record_healthy( message )
        return

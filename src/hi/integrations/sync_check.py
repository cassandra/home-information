"""
Per-integration sync-check state, and the integration-agnostic delta
primitive used to compute it.

Issue #283: a periodic background probe surfaces a "needs-sync"
signal when an integration's HI representation has drifted from
upstream. The probe never modifies entities — the user always
chooses when to invoke Refresh. Per-integration probe logic lives in
each ``IntegrationSynchronizer.check_needs_sync()`` override, which
returns a ``SyncDelta``; sync-check rides on the same opt-in surface
as full sync (an integration without a synchronizer naturally opts
out of the periodic drift check too). The framework monitor wraps
the returned delta into a ``SyncCheckResult`` (delta + timestamp +
summary) and caches it. The cache entry is the *last known state of
the check*, not a "warning flag" — a successful Refresh records a
zero-delta result with a current timestamp so the UI can show
"verified up to date at HH:MM".

State is stored via ``django.core.cache`` (Redis-backed in
production); no DB model. Frozen dataclasses pickle cleanly through
the cache backend, so no custom serialization is needed; the cache
TTL bounds the impact of any class rename.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set

from django.core.cache import cache

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.enums import LabeledEnum

from .transient_models import IntegrationKey

logger = logging.getLogger(__name__)


class SyncCheckOutcome( LabeledEnum ):
    """
    Per-integration result classification used by the framework
    monitor's bookkeeping. Not user-facing — this drives the cycle's
    summary log line and tests, not the UI banner.
    """
    OPTED_OUT  = ( 'Opted Out'  , 'Integration does not implement sync-check.' )
    IN_SYNC    = ( 'In Sync'    , 'Upstream and HI match as of this check.' )
    NEEDS_SYNC = ( 'Needs Sync' , 'Upstream has changes not yet imported.' )
    ERROR      = ( 'Error'      , 'The probe failed; the cycle continues.' )


@dataclass(frozen=True)
class SyncDelta:
    """
    Result of comparing two integration-key sets — what the
    synchronizer's ``check_needs_sync()`` returns. Integration-
    agnostic; the convention is that ``added`` contains keys upstream
    but not in HI, and ``removed`` contains keys in HI but not
    upstream. Update detection (key-present-on-both-sides but content
    changed) is out of scope for v1.

    Both sets contain ``IntegrationKey`` instances so comparison and
    hashing automatically apply the canonical normalization
    (``IntegrationKey.__post_init__``) — the same canonicalization
    that produced the stored ``entity.integration_key`` values. The
    probe never has to know about the normalization rule.
    """
    added   : Set[ IntegrationKey ] = field( default_factory = set )
    removed : Set[ IntegrationKey ] = field( default_factory = set )

    @property
    def added_count(self) -> int:
        return len( self.added )

    @property
    def removed_count(self) -> int:
        return len( self.removed )

    @property
    def needs_sync(self) -> bool:
        return bool( self.added or self.removed )


@dataclass(frozen=True)
class SyncCheckResult:
    """
    Cached state for one integration: the most recent ``SyncDelta``
    plus when the check ran and a short human-readable summary for
    the UI. Always present after the first cycle (or after a
    successful Refresh) — even when nothing has drifted, the
    zero-delta result records "verified up to date at HH:MM".
    """
    delta             : SyncDelta
    last_checked_at   : datetime
    summary_message   : str

    @property
    def needs_sync(self) -> bool:
        return self.delta.needs_sync


class IntegrationSyncCheck:
    """
    Namespace for the sync-check primitives: cache access, the
    optional set-comparison helper, and the result builders. Class
    methods rather than module-level functions so call sites carry
    the ``IntegrationSyncCheck.`` prefix and group naturally.
    """
    
    INTERVAL_SECS = 4 * 60 * 60
    
    _CACHE_TTL_SECS = INTERVAL_SECS * 2
    _CACHE_KEY_PREFIX = 'integrations:sync_check:'

    @classmethod
    def _cache_key( cls, integration_id : str ) -> str:
        return f'{cls._CACHE_KEY_PREFIX}{integration_id}'

    @staticmethod
    def compute_delta( upstream_keys : Set[ IntegrationKey ],
                       current_keys  : Set[ IntegrationKey ] ) -> SyncDelta:
        """
        Pure utility for integrations whose check reduces to comparing
        a set of upstream IntegrationKeys against a set of HI
        IntegrationKeys. Most integrations call this from inside
        their ``check_needs_sync()``; integrations with non-set
        semantics can build a ``SyncDelta`` directly.

        Set arithmetic on ``IntegrationKey`` instances picks up the
        canonical normalization automatically (via the dataclass's
        ``__hash__`` / ``__eq__``), so the probe never has to know
        about the normalization rule. Callers feed already-filtered
        sets so the counts match what Refresh would actually act on,
        not what the upstream raw response contains.
        """
        return SyncDelta(
            added   = set( upstream_keys ) - set( current_keys ),
            removed = set( current_keys )  - set( upstream_keys ),
        )

    @classmethod
    def get_state( cls, integration_id : str ) -> Optional[ SyncCheckResult ]:
        """Return the most recent cached result, or None if no probe
        has written one (or the entry has expired)."""
        if not integration_id:
            return None
        return cache.get( cls._cache_key( integration_id ) )

    @classmethod
    def set_state( cls,
                   integration_id : str,
                   result         : SyncCheckResult ) -> None:
        """Write a probe result to the cache. The TTL is bounded so a
        stopped monitor cannot leave forever-old state visible. Fires
        a transition alarm when the recorded state moves from
        no-prior / in-sync to needs-sync (see ``_should_alarm``);
        in-progress drift does not re-alarm cycle after cycle.

        Concurrency: this is a read-modify-write on the cache without
        a lock. The two callers — the framework monitor's probe cycle
        and ``record_sync_complete`` via the synchronizer's post-sync
        hook — can theoretically run concurrently if a user-triggered
        Refresh overlaps a probe cycle. By inspection the
        interleavings are benign: duplicate-direction races (both
        writers see prior=clean and call ``_fire_needs_sync_alarm``)
        collapse to a single alert via ``AlertManager``'s
        signature-based dedup, and opposite-direction races worst
        case fire a stale alarm for drift that was just cleared
        — dismissable, rare, no correctness impact. A Redis lock
        would prevent it but trades real cache-backend portability
        risk (LocMemCache in tests) for a marginal UX win, so we
        intentionally do not lock here."""
        if not integration_id:
            return
        prior = cls.get_state( integration_id )
        cache.set(
            cls._cache_key( integration_id ),
            result,
            timeout = cls._CACHE_TTL_SECS,
        )
        logger.debug(
            f'sync-check state recorded for {integration_id}: '
            f'needs_sync={result.needs_sync} '
            f'added={result.delta.added_count} '
            f'removed={result.delta.removed_count}'
        )
        if cls._should_alarm( prior = prior, current = result ):
            # Alarm delivery failures must not break the cache write
            # — the probe state is already persisted; the next
            # clear→set transition will re-attempt notification.
            try:
                cls._fire_needs_sync_alarm(
                    integration_id = integration_id,
                    result = result,
                )
            except Exception as e:
                logger.warning(
                    f'Failed to fire needs-sync alarm for '
                    f'{integration_id}: {e}'
                )

    @staticmethod
    def _should_alarm( prior   : Optional[ SyncCheckResult ],
                       current : SyncCheckResult ) -> bool:
        """Notification gate. Fires only on the clear → needs-sync
        transition: prior was None (first probe / cache expired) or
        in-sync, AND current reports needs-sync. Drift that persists
        across cycles (needs-sync → needs-sync) does not re-alarm —
        the user has already been told. Refresh-induced
        needs-sync → in-sync transitions are not a notification
        direction."""
        if not current.needs_sync:
            return False
        if prior is None:
            return True
        return not prior.needs_sync

    @staticmethod
    def _fire_needs_sync_alarm( integration_id : str,
                                result         : SyncCheckResult ) -> None:
        """Construct and queue an INFO-level alarm for a transition
        into the needs-sync state. Per-integration unique signature
        (``integrations.needs_sync.<integration_id>``) so two
        integrations both reporting drift surface as two distinct
        alerts. Lifetime is ``Alarm.MAX_LIFETIME_SECS`` — the
        canonical "until acknowledged" value (see
        ``hi/apps/alert/alarm.py``)."""
        from hi.apps.alert.alarm import Alarm
        from hi.apps.alert.alert_manager import AlertManager
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        from hi.apps.sense.transient_models import SensorResponse

        from .transient_models import IntegrationKey

        alarm_integration_key = IntegrationKey(
            integration_id = 'integrations',
            integration_name = f'needs_sync.{integration_id}',
        )
        sensor_response = SensorResponse(
            integration_key = alarm_integration_key,
            value = 'NEEDS_SYNC',
            timestamp = result.last_checked_at,
            sensor = None,
            detail_attrs = {
                'Added'        : str( result.delta.added_count ),
                'Removed'      : str( result.delta.removed_count ),
                'Last Checked' : result.last_checked_at.strftime(
                    '%Y-%m-%d %H:%M:%S',
                ),
            },
            source_image_url = None,
            has_video_stream = False,
        )
        alarm = Alarm(
            alarm_source = AlarmSource.INTEGRATION,
            alarm_type = f'integrations.needs_sync.{integration_id}',
            alarm_level = AlarmLevel.INFO,
            title = result.summary_message,
            sensor_response_list = [ sensor_response ],
            security_level = SecurityLevel.OFF,
            alarm_lifetime_secs = Alarm.MAX_LIFETIME_SECS,
            timestamp = datetimeproxy.now(),
        )
        AlertManager().add_alarm( alarm )

    @classmethod
    def clear_state( cls, integration_id : str ) -> None:
        """Drop the cached state entirely. Used on integration removal;
        post-Refresh uses ``record_sync_complete`` instead so the UI
        keeps a "verified at HH:MM" indicator rather than going dark.
        """
        if not integration_id:
            return
        cache.delete( cls._cache_key( integration_id ) )
        logger.debug( f'sync-check state cleared for {integration_id}' )

    @classmethod
    def record_sync_complete( cls,
                              integration_id    : str,
                              integration_label : str ) -> None:
        """Called after a successful Refresh: the integration is by
        definition in sync, so we write a zero-delta result with a
        current timestamp. UI surfaces the verified state and the
        next probe cycle naturally re-confirms or detects new drift.
        """
        cls.set_state(
            integration_id = integration_id,
            result = cls.build_result(
                delta = SyncDelta(),
                integration_label = integration_label,
            ),
        )

    @classmethod
    def build_result( cls,
                      delta             : SyncDelta,
                      integration_label : str,
                      last_checked_at   : Optional[ datetime ] = None,
                      ) -> SyncCheckResult:
        """Wrap a ``SyncDelta`` into a ``SyncCheckResult`` with a
        sensible default summary message and timestamp. The framework
        monitor calls this with the delta returned from each
        synchronizer's ``check_needs_sync()``.
        """
        if last_checked_at is None:
            last_checked_at = datetimeproxy.now()
        return SyncCheckResult(
            delta = delta,
            last_checked_at = last_checked_at,
            summary_message = cls._summary_message(
                delta = delta,
                integration_label = integration_label,
            ),
        )

    @staticmethod
    def _summary_message( delta             : SyncDelta,
                          integration_label : str ) -> str:
        """Pure-information summary of the most recent check. The
        Refresh call-to-action is rendered as a real link by the
        manage-page banner template (so clicking it opens the
        pre-sync modal); it is intentionally not embedded in this
        string. The same string flows into the sidebar tooltip,
        where a "click here" suffix would be misleading."""
        if not delta.needs_sync:
            return f'{integration_label} is up to date.'
        pieces = []
        if delta.added_count:
            noun = 'item' if delta.added_count == 1 else 'items'
            pieces.append( f'{delta.added_count} new {noun} upstream' )
        if delta.removed_count:
            noun = 'item' if delta.removed_count == 1 else 'items'
            pieces.append( f'{delta.removed_count} {noun} removed upstream' )
        return f'{integration_label}: {", ".join(pieces)}.'

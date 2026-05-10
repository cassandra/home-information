import logging
import threading
from typing import Any, Dict, Optional

from asgiref.sync import sync_to_async

from hi.apps.common.singleton import Singleton
from hi.apps.control.models import Controller
from hi.apps.entity.models import EntityState
from hi.apps.sense.models import Sensor

from .transient_models import IntegrationKey

logger = logging.getLogger(__name__)


class IntegrationMetadataCache( Singleton ):
    """Process-wide, lazily-warmed cache of EntityState metadata
    that integration converters need at value-translation time.

    Polling loops are hot paths and the inbound and outbound
    converters need per-entity metadata (today: stored units;
    potentially more in the future) on every call. Caching avoids
    per-call DB queries; the underlying fields are set at creation
    and rarely change in practice, so a process-lifetime cache
    with no active invalidation is the right trade-off (the
    workaround for the rare edit is a process restart).

    Keyed by ``IntegrationKey``. Each entry is a small dict so
    additional metadata can be added later without changing the
    API surface. Today the only entry key is ``units`` (the
    EntityState.units string, or None when the EntityState has
    no units).

    Concurrency: bulk-warmup and lazy single-row fills take the
    write lock; reads of an already-populated entry are unlocked
    (CPython dict reads are atomic for our access pattern).
    """

    def __init_singleton__(self):
        self._cache : Dict[ IntegrationKey, Dict[str, Any] ] = {}
        self._lock = threading.Lock()
        self._warmed = False
        return

    def get_entry(
            self, integration_key : IntegrationKey,
    ) -> Dict[str, Any]:
        """Return the cached metadata dict for the given
        ``integration_key``. Triggers a single bulk warmup on the
        first call across the process; entities created after
        warmup are filled lazily on miss. Sync API; use
        ``get_entry_async`` from async contexts to avoid Django's
        SynchronousOnlyOperation guard during DB-touching paths."""
        if not self._warmed:
            self._warmup()
        entry = self._cache.get( integration_key )
        if entry is not None:
            return entry
        return self._lazy_fill( integration_key )

    async def get_entry_async(
            self, integration_key : IntegrationKey,
    ) -> Dict[str, Any]:
        """Async variant of ``get_entry``. After the cache is
        warmed, reads are pure-Python dict accesses and the
        sync_to_async hop is essentially free; before warm and on
        lazy-fill misses, the DB lookup happens in a thread pool
        so it's safe to call from async monitor contexts."""
        if self._warmed and integration_key in self._cache:
            return self._cache[ integration_key ]
        return await sync_to_async(
            self.get_entry, thread_sensitive=True,
        )( integration_key )

    def _warmup(self):
        """One-shot bulk load of every known integration_key.

        Assumes any Sensor/Controller pair sharing an
        ``integration_key`` references the same EntityState (enforced
        by ``HiModelHelper``; ``integration_id`` namespacing prevents
        cross-integration collisions). Sensor entries win on overlap;
        a warning fires if the Controller's entry would have
        disagreed — canary for invariant violations."""
        with self._lock:
            if self._warmed:
                return
            for sensor in Sensor.objects.select_related( 'entity_state' ).all():
                key = sensor.integration_key
                if key is None:
                    continue
                self._cache[ key ] = self._build_entry( sensor.entity_state )
            for controller in Controller.objects.select_related( 'entity_state' ).all():
                key = controller.integration_key
                if key is None:
                    continue
                controller_entry = self._build_entry( controller.entity_state )
                existing = self._cache.get( key )
                if existing is None:
                    self._cache[ key ] = controller_entry
                    continue
                if existing != controller_entry:
                    logger.warning(
                        f'IntegrationMetadataCache invariant violated for '
                        f'{key}: divergent Sensor/Controller metadata '
                        f'({existing} vs {controller_entry}). See class docs.'
                    )
            self._warmed = True

    def _lazy_fill(
            self, integration_key : IntegrationKey,
    ) -> Dict[str, Any]:
        """Single-row fill on a post-warmup miss (entity created
        after warmup). Falls back to an empty entry when the key
        resolves to nothing so subsequent misses don't re-query."""
        entity_state = self._lookup_entity_state( integration_key )
        entry = (
            self._build_entry( entity_state )
            if entity_state is not None
            else { 'units': None }
        )
        with self._lock:
            self._cache.setdefault( integration_key, entry )
        return self._cache[ integration_key ]

    @staticmethod
    def _lookup_entity_state(
            integration_key : IntegrationKey,
    ) -> Optional[ EntityState ]:
        try:
            return Sensor.objects.select_related( 'entity_state' ).get(
                integration_id = integration_key.integration_id,
                integration_name = integration_key.integration_name,
            ).entity_state
        except Sensor.DoesNotExist:
            pass
        try:
            return Controller.objects.select_related( 'entity_state' ).get(
                integration_id = integration_key.integration_id,
                integration_name = integration_key.integration_name,
            ).entity_state
        except Controller.DoesNotExist:
            return None

    @staticmethod
    def _build_entry( entity_state : EntityState ) -> Dict[str, Any]:
        return {
            'units': entity_state.units or None,
        }

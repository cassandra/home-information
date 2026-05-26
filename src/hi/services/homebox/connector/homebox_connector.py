import logging
from typing import Dict, List, Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from hi.apps.entity.models import Entity
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.connector.external_view_data import ExternalViewData
from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.connector.sync_check import IntegrationSyncCheck, SyncDelta
from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.enums import IntegrationCapability
from hi.integrations.transient_models import IntegrationKey

from hi.services.homebox.connector.hb_external_view_resolver import HomeBoxExternalViewResolver
from hi.services.homebox.hb_controller import HomeBoxController
from hi.services.homebox.monitors import HomeBoxMonitor
from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_manager import HomeBoxManager
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_mixins import HomeBoxMixin
from hi.services.homebox.hb_models import HbItem
from hi.services.homebox.hb_entity_factory import HbEntityFactory

logger = logging.getLogger(__name__)


class HomeBoxConnector( IntegrationConnector, HomeBoxMixin ):

    def get_integration_metadata(self):
        return HbMetaData

    def get_monitor(self) -> HomeBoxMonitor:
        return HomeBoxMonitor()

    def get_controller(self) -> HomeBoxController:
        return HomeBoxController()

    def get_health_status_provider(self) -> HealthStatusProvider:
        return HomeBoxManager()

    def get_external_view_data(self, entity: Entity) -> Optional[ExternalViewData]:
        return HomeBoxExternalViewResolver().get_external_view_data(entity)

    def get_description(self, is_initial_connect: bool) -> Optional[str]:
        return (
            'HomeBox Labels and Locations are kept as metadata on '
            'each item, not as separate organizational concepts in HI.'
        )

    async def check_needs_sync(self) -> Optional[SyncDelta]:
        """Issue #283 — sync-check probe for HomeBox.

        Uses the lightweight items-summary endpoint (one API call,
        no per-item details) to build the upstream IntegrationKey
        set, compares against the IntegrationKeys of HomeBox-attached
        HI entities, and returns the resulting ``SyncDelta``.
        Convention matched to
        ``HbConverter.hb_item_to_integration_key``: each HomeBox
        item becomes one HI entity whose ``integration_name`` is
        ``str(item.id)``. Adds/removes only — update detection via
        timestamps is deferred.
        """
        hb_manager = await self.hb_manager_async()
        if hb_manager is None:
            # Manager not yet initialized — let the next probe cycle
            # try again. Returning None opts this cycle out cleanly.
            return None
        summary_list = await hb_manager.fetch_hb_items_summary_from_api_async()
        # ``archived: true`` upstream is HomeBox's "no longer in
        # active use" marker. Treat archived items as if they were
        # absent so the sync-check correctly reports them as removed
        # — see ``_sync_helper_entities`` for the matching filter on
        # the full-detail fetch.
        upstream_keys = {
            IntegrationKey(
                integration_id = HbMetaData.integration_id,
                integration_name = str( item['id'] ),
            )
            for item in summary_list
            if item.get('id') is not None
            and item.get('archived') is not True
        }
        current_keys = await sync_to_async( self._get_current_integration_keys )()
        return IntegrationSyncCheck.compute_delta(
            upstream_keys = upstream_keys,
            current_keys = current_keys,
        )

    @staticmethod
    def _get_current_integration_keys() -> set:
        # Scope to actively-attached (EXTERNAL) entities. Detached
        # entities for the same integration are picked up by the
        # auto-reconnect path during sync, not by this primary-match
        # probe.
        return {
            IntegrationKey(
                integration_id = integration_id,
                integration_name = integration_name,
            )
            for integration_id, integration_name in Entity.objects.external_for(
                integration_id = HbMetaData.integration_id,
            ).values_list( 'integration_id', 'integration_name' )
        }

    def _sync_impl( self, is_initial_connect: bool ) -> IntegrationSyncResult:
        hb_manager = self.hb_manager()
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_connect = is_initial_connect ),
        )

        if not hb_manager.hb_client:
            health_status = hb_manager.health_status
            reason = health_status.last_message or 'HomeBox integration is disabled or not configured.'
            logger.debug( f'HomeBox client not available: {reason}' )
            result.error_list.append( f'Cannot sync HomeBox: {reason}' )
            return result

        try:
            item_list = hb_manager.fetch_hb_items_from_api()
        except Exception as e:
            # Runtime API call hit a transient upstream problem (login
            # failure, NON_JSON response, etc.). Surface the underlying
            # message rather than propagating a 500. The HbClient's
            # lazy-login path will retry on the next sync attempt,
            # naturally recovering once the upstream is healthy.
            logger.exception( 'HomeBox sync failed during fetch.' )
            result.error_list.append( f'Cannot sync HomeBox: {e}' )
            return result

        result.info_list.append( f'Found {len(item_list)} current HomeBox items.' )

        # Existing-entity updates do not need re-placement; only
        # newly-created entities surface in the dispatcher.
        created_entities = self._sync_helper_entities(
            item_list = item_list, result = result )
        result.created_entities = created_entities
        return result

    # group_entities_for_placement: no override. HomeBox inherits
    # the gateway base default (group by EntityType). Today
    # ``HbConverter.hb_item_to_entity_type`` stamps every imported
    # item as ``EntityType.OTHER``, so the result is a single
    # ``Other`` group — functionally equivalent to ungrouped, just
    # with an extra label level. A future HomeBox-specific override
    # (e.g. by upstream Location, read from ``integration_payload``)
    # will replace this default.

    def _sync_helper_entities( self,
                               item_list: List[HbItem],
                               result: IntegrationSyncResult ) -> List[Entity]:
        """Sync HomeBox items and return newly-created entities (for
        the caller to feed into group_entities_for_placement).
        Existing-entity updates do not contribute — they don't need
        re-placement."""
        integration_key_to_item = dict()
        skipped_archived = 0
        for item in item_list:
            # ``archived: true`` upstream means the item is no
            # longer in active use. Skip it so the sync's removal
            # branch picks up its HI counterpart on the same pass:
            # SAFE removal handles user-data preservation if the
            # operator added attributes; hard-delete otherwise.
            # Mirrored in ``check_needs_sync`` so the sync-check
            # delta agrees with what the full sync will do.
            if item.archived is True:
                skipped_archived += 1
                continue
            try:
                integration_key = HbConverter.hb_item_to_integration_key( hb_item = item )
                integration_key_to_item[integration_key] = item
            except Exception as e:
                result.error_list.append( f'Ignoring HomeBox item due to missing/invalid id: {e}' )
            continue
        if skipped_archived:
            result.info_list.append(
                f'Skipped {skipped_archived} archived HomeBox item(s).'
            )

        integration_key_to_entity = self._get_existing_hb_entities( result = result )
        result.info_list.append( f'Found {len(integration_key_to_entity)} existing HomeBox items.' )

        # Issue #281 reconnect pre-pass (framework-level). Any
        # disconnected entity whose previous identity matches an
        # unmatched upstream item is reconnected in place and added
        # to integration_key_to_entity, so the main loop below treats
        # it as primary-matched without any reconnect-aware branching.
        self.reconnect_disconnected_items(
            integration_key_to_upstream = integration_key_to_item,
            integration_key_to_entity = integration_key_to_entity,
            result = result,
        )

        created_entities: List[Entity] = []
        with transaction.atomic():
            for integration_key, hb_item in integration_key_to_item.items():
                entity = integration_key_to_entity.get( integration_key )
                if entity:
                    self._update_entity(
                        entity = entity,
                        item = hb_item,
                        result = result,
                    )
                else:
                    entity = self._create_entity( item = hb_item, result = result )
                    created_entities.append( entity )

                # Attributes are fetched live by the connector.
                continue

            for integration_key, entity in integration_key_to_entity.items():
                if integration_key not in integration_key_to_item:
                    self._remove_entity( entity = entity, result = result )
                continue
        return created_entities

    def _rebuild_integration_components( self,
                                         entity   : Entity,
                                         upstream : HbItem,
                                         result   : IntegrationSyncResult ):
        """Reconnect hook: dispatch to ``HbEntityFactory`` with the existing
        entity so integration-owned components are repopulated on the
        previously-disconnected entity rather than creating a new one."""
        HbEntityFactory.create_models_for_hb_item(
            hb_item = upstream,
            capability = IntegrationCapability.CONNECT,
            entity = entity,
        )
        return

    def _get_existing_hb_entities( self, result : IntegrationSyncResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing HomeBox entities.' )
        integration_key_to_entity = dict()

        # Scope to actively-attached (EXTERNAL) entities. Detached
        # rows for the same integration are picked up by the
        # auto-reconnect path, not the primary-match scan.
        entity_queryset = Entity.objects.external_for(
            integration_id = HbMetaData.integration_id,
        )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'Item found without valid HomeBox Id: {entity}' )
                mock_hb_device_id = 1000000 + entity.id  # We need a (unique) placeholder for removals
                integration_key = IntegrationKey(
                    integration_id = HbMetaData.integration_id,
                    integration_name = str( mock_hb_device_id ),
                )

            integration_key_to_entity[integration_key] = entity
            continue

        return integration_key_to_entity

    def _create_entity( self,
                        item : HbItem,
                        result : IntegrationSyncResult ) -> Entity:
        entity = HbEntityFactory.create_models_for_hb_item(
            hb_item = item,
            capability = IntegrationCapability.CONNECT,
        )
        result.created_list.append( entity.name )
        return entity

    def _update_entity( self,
                        entity : Entity,
                        item : HbItem,
                        result : IntegrationSyncResult ):
        # update_models_for_hb_item returns a list of change
        # description strings — non-empty means at least one
        # operator-visible change was made.
        change_messages = HbEntityFactory.update_models_for_hb_item(
            entity = entity, hb_item = item,
        )
        if change_messages and entity.name not in result.updated_list:
            result.updated_list.append( entity.name )
        return

    def _remove_entity( self,
                        entity : Entity,
                        result : IntegrationSyncResult ):
        self._remove_entity_intelligently( entity, result )
        return

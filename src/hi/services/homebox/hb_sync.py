import logging
from typing import Dict

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity

from hi.integrations.transient_models import IntegrationKey
from hi.integrations.sync_mixins import IntegrationSyncMixin

from .hb_converter import HbConverter
from .hb_metadata import HbMetaData
from .hb_mixins import HomeBoxMixin

logger = logging.getLogger(__name__)


class HomeBoxSynchronizer( HomeBoxMixin, IntegrationSyncMixin ):

    SYNCHRONIZATION_LOCK_NAME = 'hb_integration_sync'

    def __init__(self):
        return

    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'HomeBox integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
            logger.exception( e )
            return ProcessingResult(
                title = 'HomeBox Import Result',
                error_list = [ str(e) ],
            )
        finally:
            logger.debug( 'HomeBox integration sync ended.' )

    def _sync_helper( self ) -> ProcessingResult:
        hb_manager = self.hb_manager()
        result = ProcessingResult( title = 'HomeBox Import Result' )

        if not hb_manager.hb_client:
            logger.debug( 'HomeBox client not created. HomeBox integration disabled?' )
            result.error_list.append( 'Sync problem. HomeBox integration disabled?' )
            return result

        item_list = hb_manager.fetch_hb_items_from_api()
        result.message_list.append( f'Found {len(item_list)} current HomeBox items.' )

        integration_key_to_item = dict()
        for item in item_list:
            try:
                integration_key = HbConverter.hb_item_to_integration_key( hb_item = item )
                integration_key_to_item[integration_key] = item
            except Exception as e:
                result.error_list.append( f'Ignoring HomeBox item due to missing/invalid id: {e}' )
            continue

        integration_key_to_entity = self._get_existing_hb_entities( result = result )
        result.message_list.append( f'Found {len(integration_key_to_entity)} existing HomeBox entities.' )

        with transaction.atomic():
            for integration_key, item in integration_key_to_item.items():
                entity = integration_key_to_entity.get( integration_key )
                if entity:
                    self._update_entity( entity = entity,
                                         item = item,
                                         result = result )
                else:
                    self._create_entity( item = item,
                                         result = result )
                continue

            for integration_key, entity in integration_key_to_entity.items():
                if integration_key not in integration_key_to_item:
                    self._remove_entity( entity = entity,
                                         result = result )
                continue

        label_list = hb_manager.fetch_hb_labels_from_api()
        result.message_list.append( f'Found {len(label_list)} current HomeBox labels.' )

        location_list = hb_manager.fetch_hb_locations_from_api()
        result.message_list.append( f'Found {len(location_list)} current HomeBox locations.' )

        maitenance_list = hb_manager.fetch_hb_maintenances_from_api()
        result.message_list.append( f'Found {len(maitenance_list)} current HomeBox maintenances.' )

        return result

    def _get_existing_hb_entities( self, result : ProcessingResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing HomeBox entities.' )
        integration_key_to_entity = dict()

        entity_queryset = Entity.objects.filter( integration_id = HbMetaData.integration_id )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'Entity found without valid HomeBox Id: {entity}' )
                mock_hb_device_id = 1000000 + entity.id  # We need a (unique) placeholder for removals
                integration_key = IntegrationKey(
                    integration_id = HbMetaData.integration_id,
                    integration_name = str( mock_hb_device_id ),
                )

            integration_key_to_entity[integration_key] = entity
            continue

        return integration_key_to_entity

    def _create_entity( self,
                        item,
                        result : ProcessingResult ):
        entity = HbConverter.create_models_for_hb_item( hb_item = item )

        result.message_list.append( f'Created HomeBox entity: {entity}' )
        return

    def _update_entity( self,
                        entity : Entity,
                        item,
                        result : ProcessingResult ):
        message_list = HbConverter.update_models_for_hb_item(
            entity = entity,
            hb_item = item,
        )

        if message_list:
            result.message_list.append(
                f'Updated HomeBox entity: {entity} ({", ".join(message_list)})'
            )
        else:
            result.message_list.append( f'No changes found for HomeBox entity: {entity}' )
        return

    def _remove_entity( self,
                        entity : Entity,
                        result : ProcessingResult ):
        self._remove_entity_intelligently( entity, result, 'HomeBox' )
        return

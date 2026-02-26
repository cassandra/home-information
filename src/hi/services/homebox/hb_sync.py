import logging
from typing import Dict, List

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity, EntityAttribute

from hi.integrations.transient_models import IntegrationKey
from hi.integrations.sync_mixins import IntegrationSyncMixin

from .hb_converter import HbConverter
from .hb_metadata import HbMetaData
from .hb_mixins import HomeBoxMixin
from .hb_client.helpers.item import HbItem

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

        self._sync_helper_entities( item_list = item_list, result = result )

        return result
    
    def _sync_helper_entities( self, 
                               item_list: List[HbItem], 
                               result: ProcessingResult ):
        
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
                    
                self._sync_helper_entity_attributes( 
                    entity = entity,
                    hb_item = hb_item,
                    result = result,
                )
                continue

            for integration_key, entity in integration_key_to_entity.items():
                if integration_key not in integration_key_to_item:
                    self._remove_entity( entity = entity, result = result )
                continue

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
                        item : HbItem,
                        result : ProcessingResult ) -> Entity:
        entity = HbConverter.create_models_for_hb_item( hb_item = item )

        result.message_list.append( f'Created HomeBox entity: {entity}' )
        return entity

    def _update_entity( self,
                        entity : Entity,
                        item : HbItem,
                        result : ProcessingResult ):
        message_list = HbConverter.update_models_for_hb_item( entity = entity, hb_item = item )

        if message_list:
            result.message_list.append( f'Updated HomeBox entity: {entity} ({", ".join(message_list)})' )
        else:
            result.message_list.append( f'No changes found for HomeBox entity: {entity}' )
        return

    def _remove_entity( self,
                        entity : Entity,
                        result : ProcessingResult ):
        self._remove_entity_intelligently( entity, result, 'HomeBox' )
        return

    def _sync_helper_entity_attributes( self,
                                        entity: Entity,
                                        hb_item: HbItem,
                                        result: ProcessingResult ):
        attribute_message_list = list()

        integration_key_to_regular_field = dict()
        hb_field_list = HbConverter.hb_item_to_attribute_field_list( hb_item = hb_item )
        for order_id, hb_field in enumerate( hb_field_list ):
            if not isinstance( hb_field, dict ):
                continue

            integration_key = HbConverter.hb_field_to_integration_key( hb_field = hb_field )
            if integration_key:
                integration_key_to_regular_field[integration_key] = (hb_field, order_id)

        integration_key_to_attachment = dict()
        attachment_list = HbConverter.hb_item_to_attachment_list( hb_item = hb_item )
        for order_id, hb_attachment in enumerate( attachment_list ):
            if not isinstance( hb_attachment, dict ):
                continue

            integration_key = HbConverter.hb_attachment_to_integration_key( hb_attachment = hb_attachment )
            if integration_key:
                integration_key_to_attachment[integration_key] = ( hb_attachment, order_id )

        active_integration_keys = set(integration_key_to_regular_field.keys())
        active_integration_keys.update(integration_key_to_attachment.keys())

        integration_key_to_attr = self._get_existing_hb_attributes(entity = entity)

        with transaction.atomic():

            for integration_key, field_data in integration_key_to_regular_field.items():
                hb_field, order_id = field_data
                attribute = integration_key_to_attr.get( integration_key )

                if attribute:
                    self._update_attribute(
                        attribute = attribute,
                        hb_field = hb_field,
                        order_id = order_id,
                        message_list = attribute_message_list,
                        updated_prefix = 'Field attribute updated',
                    )
                else:
                    created_attribute = self._create_attribute(
                        entity = entity,
                        hb_field = hb_field,
                        order_id = order_id,
                    )
                    if created_attribute:
                        integration_key_to_attr[integration_key] = created_attribute
                        attribute_message_list.append( f'Field attribute added: {created_attribute.name}' )
                continue

            for integration_key, hb_attachment in integration_key_to_attachment.items():
                hb_attachment, order_id = hb_attachment
                attribute = integration_key_to_attr.get( integration_key )

                if attribute:
                    self._update_attachment_attribute(
                        attribute = attribute,
                        hb_attachment = hb_attachment,
                        order_id = order_id,
                        message_list = attribute_message_list,
                        updated_prefix = 'Attachment attribute updated',
                    )
                else:
                    created_attribute = self._create_attachment_attribute(
                        entity = entity,
                        hb_attachment = hb_attachment,
                        order_id = order_id,
                    )
                    if created_attribute:
                        integration_key_to_attr[integration_key] = created_attribute
                        attribute_message_list.append( f'Attachment attribute added: {created_attribute.name}' )
                continue

            for field_key, attribute in list( integration_key_to_attr.items() ):
                if attribute.entity_id != entity.id:
                    continue

                if field_key not in active_integration_keys:
                    self._remove_attribute( attribute = attribute, message_list = attribute_message_list )
                    del integration_key_to_attr[field_key]
                continue

        if attribute_message_list:
            result.message_list.append( f'Updated HomeBox entity attributes: {entity} ({", ".join(attribute_message_list)})' )
        return
    
    def _get_existing_hb_attributes( self, entity: Entity ) -> Dict[ IntegrationKey, EntityAttribute ]:
        integration_key_to_attribute = dict()

        queryset = entity.attributes.filter( integration_key_str__isnull = False ).exclude( integration_key_str = '' )

        for attribute in queryset:
            try:
                integration_key = IntegrationKey.from_string( attribute.integration_key_str )
            except Exception:
                logger.debug( f'Ignoring entity attribute with invalid integration key: {attribute.integration_key_str}' )
                continue

            integration_key_to_attribute[integration_key] = attribute

        return integration_key_to_attribute

    def _create_attribute( self,
                           entity: Entity,
                           hb_field: dict,
                           order_id: int ) -> EntityAttribute:
        return HbConverter.create_attribute_from_hb_field(
            entity = entity,
            hb_field = hb_field,
            order_id = order_id,
        )

    def _update_attribute( self,
                           attribute: EntityAttribute,
                           hb_field: dict,
                           order_id: int,
                           message_list: List[str],
                           updated_prefix: str ):
        was_changed = HbConverter.update_attribute_from_hb_field(
            attribute = attribute,
            hb_field = hb_field,
            order_id = order_id,
        )
        if was_changed:
            message_list.append( f'{updated_prefix}: {HbConverter.hb_field_to_attribute_name( hb_field = hb_field )}' )
        return

    def _create_attachment_attribute( self,
                                      entity: Entity,
                                      hb_attachment: dict,
                                      order_id: int ) -> EntityAttribute:
        return HbConverter.create_attribute_from_hb_attachment(
            entity = entity,
            hb_attachment = hb_attachment,
            order_id = order_id,
        )

    def _update_attachment_attribute( self,
                                      attribute: EntityAttribute,
                                      hb_attachment: dict,
                                      order_id: int,
                                      message_list: List[str],
                                      updated_prefix: str ):
        was_changed = HbConverter.update_attribute_from_hb_attachment(
            attribute = attribute,
            hb_attachment = hb_attachment,
            order_id = order_id,
        )
        if was_changed:
            message_list.append( f'{updated_prefix}: {HbConverter.hb_attachment_to_attribute_name( hb_attachment = hb_attachment )}' )
        return

    def _remove_attribute( self,
                           attribute: EntityAttribute,
                           message_list: List[str] ):
        old_name = attribute.name
        attribute.delete()
        message_list.append( f'Field attribute removed: {old_name}' )
        return

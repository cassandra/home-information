import logging
from typing import Dict, List, Optional

from django.db import transaction

from hi.apps.entity.models import Entity, EntityAttribute

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from .hb_converter import HbConverter
from .hb_metadata import HbMetaData
from .hb_mixins import HomeBoxMixin
from .hb_models import HbItem

logger = logging.getLogger(__name__)


class HomeBoxSynchronizer( IntegrationSynchronizer, HomeBoxMixin ):

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        return (
            'HomeBox Labels and Locations are kept as metadata on '
            'each item, not as separate organizational concepts in HI.'
        )

    def _sync_impl( self, is_initial_import: bool ) -> IntegrationSyncResult:
        hb_manager = self.hb_manager()
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_import = is_initial_import ),
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
        if created_entities:
            result.placement_input = self.group_entities_for_placement(
                entities = created_entities,
            )
        return result

    # group_entities_for_placement: HomeBox has no domain notion of
    # grouping, so the base-class default (all-ungrouped) is exactly
    # what we want. No override needed.

    def _sync_helper_entities( self,
                               item_list: List[HbItem],
                               result: IntegrationSyncResult ) -> List[Entity]:
        """Sync HomeBox items and return newly-created entities (for
        the caller to feed into group_entities_for_placement).
        Existing-entity updates do not contribute — they don't need
        re-placement."""
        integration_key_to_item = dict()
        for item in item_list:
            try:
                integration_key = HbConverter.hb_item_to_integration_key( hb_item = item )
                integration_key_to_item[integration_key] = item
            except Exception as e:
                result.error_list.append( f'Ignoring HomeBox item due to missing/invalid id: {e}' )
            continue

        integration_key_to_entity = self._get_existing_hb_entities( result = result )
        result.info_list.append( f'Found {len(integration_key_to_entity)} existing HomeBox items.' )

        # Issue #281 reconnect pre-pass (framework-level). Any
        # disconnected entity whose previous identity matches an
        # unmatched upstream item is reconnected in place and added
        # to integration_key_to_entity, so the main loop below treats
        # it as primary-matched without any reconnect-aware branching.
        self.reconnect_disconnected_items(
            integration_id = HbMetaData.integration_id,
            integration_label = HbMetaData.label,
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
        return created_entities

    def _rebuild_integration_components( self,
                                         entity   : Entity,
                                         upstream : HbItem,
                                         result   : IntegrationSyncResult ):
        """Issue #281: dispatch to the HomeBox converter with the
        existing-entity parameter set, so the converter repopulates
        integration-owned components on the previously-disconnected
        entity rather than creating a fresh one."""
        HbConverter.create_models_for_hb_item(
            hb_item = upstream,
            entity = entity,
        )
        return

    def _get_existing_hb_entities( self, result : IntegrationSyncResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing HomeBox entities.' )
        integration_key_to_entity = dict()

        entity_queryset = Entity.objects.filter( integration_id = HbMetaData.integration_id )
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
        entity = HbConverter.create_models_for_hb_item( hb_item = item )
        result.created_list.append( entity.name )
        return entity

    def _update_entity( self,
                        entity : Entity,
                        item : HbItem,
                        result : IntegrationSyncResult ):
        # update_models_for_hb_item returns a list of change
        # description strings — non-empty means at least one
        # operator-visible change was made.
        change_messages = HbConverter.update_models_for_hb_item(
            entity = entity, hb_item = item,
        )
        if change_messages and entity.name not in result.updated_list:
            result.updated_list.append( entity.name )
        return

    def _remove_entity( self,
                        entity : Entity,
                        result : IntegrationSyncResult ):
        self._remove_entity_intelligently( entity, result, 'HomeBox' )
        return

    def _sync_helper_entity_attributes( self,
                                        entity: Entity,
                                        hb_item: HbItem,
                                        result: IntegrationSyncResult ):
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
        attachment_list = HbConverter.hb_item_to_attachment_field_list( hb_item = hb_item )
        field_count = len( hb_field_list )
        for order_id, hb_attachment in enumerate( attachment_list, start = field_count ):
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
                        attribute_message_list.append(
                            f'Field attribute added: {created_attribute.name}'
                        )
                continue

            for integration_key, hb_attachment_tuple in integration_key_to_attachment.items():
                hb_attachment, order_id = hb_attachment_tuple
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
                        attribute_message_list.append(
                            f'Attachment attribute added: {created_attribute.name}'
                        )
                continue

            for field_key, attribute in list( integration_key_to_attr.items() ):
                if attribute.entity_id != entity.id:
                    continue

                if field_key not in active_integration_keys:
                    self._remove_attribute( attribute = attribute, message_list = attribute_message_list )
                    del integration_key_to_attr[field_key]
                continue

        # An attribute-level change still means this entity was
        # modified by the sync. Mark it in updated_list (with dedup
        # against the entity-level path above) so the operator
        # sees the entity name. Skip the mark when this entity was
        # just created — its attributes are new because the entity
        # is new, not because of a refresh-time update. Per-attribute
        # detail itself stays internal — entity-name granularity is
        # the contract.
        if (
            attribute_message_list
            and entity.name not in result.created_list
            and entity.name not in result.updated_list
        ):
            result.updated_list.append( entity.name )
        return
    
    def _get_existing_hb_attributes( self, entity: Entity ) -> Dict[ IntegrationKey, EntityAttribute ]:
        integration_key_to_attribute = dict()

        queryset = entity.attributes.filter(
            integration_key_str__isnull = False
        ).exclude( integration_key_str = '' )

        for attribute in queryset:
            try:
                integration_key = IntegrationKey.from_string( attribute.integration_key_str )
            except Exception:
                logger.debug(
                    'Ignoring entity attribute with invalid integration key: '
                    f'{attribute.integration_key_str}'
                )
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
            message = (
                f'{updated_prefix}: '
                f'{HbConverter.hb_field_to_attribute_name( hb_field = hb_field )}'
            )
            message_list.append( message )
        return

    def _remove_attribute( self,
                           attribute: EntityAttribute,
                           message_list: List[str] ):
        old_name = attribute.name
        attribute.delete()
        message_list.append( f'Field attribute removed: {old_name}' )
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
            message = (
                f'{updated_prefix}: '
                f'{HbConverter.hb_attachment_to_attribute_name( hb_attachment = hb_attachment )}'
            )
            message_list.append( message )
        return

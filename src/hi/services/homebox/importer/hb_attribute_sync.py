"""Preserved attribute-sync code from the pre-#354 copy-on-sync
architecture. Dormant — no live caller. The HomeBox Importer in #358
will adapt these into the Importer protocol's run_import method.
"""
import logging
from typing import Dict, List

from django.db import transaction

from hi.apps.entity.models import Entity, EntityAttribute

from hi.integrations.connect.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from hi.services.homebox.shared.hb_converter import HbConverter
from hi.services.homebox.shared.hb_models import HbItem
from .hb_importer import HbImporter

logger = logging.getLogger(__name__)


class HbAttributeSync:

    @classmethod
    def sync_entity_attributes( cls,
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

        integration_key_to_attr = cls.get_existing_hb_attributes( entity = entity )

        with transaction.atomic():

            for integration_key, field_data in integration_key_to_regular_field.items():
                hb_field, order_id = field_data
                attribute = integration_key_to_attr.get( integration_key )

                if attribute:
                    cls.update_attribute(
                        attribute = attribute,
                        hb_field = hb_field,
                        order_id = order_id,
                        message_list = attribute_message_list,
                        updated_prefix = 'Field attribute updated',
                    )
                else:
                    created_attribute = cls.create_attribute(
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
                    cls.update_attachment_attribute(
                        attribute = attribute,
                        hb_attachment = hb_attachment,
                        order_id = order_id,
                        message_list = attribute_message_list,
                        updated_prefix = 'Attachment attribute updated',
                    )
                else:
                    created_attribute = cls.create_attachment_attribute(
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
                    cls.remove_attribute( attribute = attribute, message_list = attribute_message_list )
                    del integration_key_to_attr[field_key]
                continue

        if (
            attribute_message_list
            and entity.name not in result.created_list
            and entity.name not in result.updated_list
        ):
            result.updated_list.append( entity.name )
        return

    @classmethod
    def get_existing_hb_attributes( cls, entity: Entity ) -> Dict[ IntegrationKey, EntityAttribute ]:
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

    @classmethod
    def create_attribute( cls,
                          entity: Entity,
                          hb_field: dict,
                          order_id: int ) -> EntityAttribute:
        return HbImporter.create_attribute_from_hb_field(
            entity = entity,
            hb_field = hb_field,
            order_id = order_id,
        )

    @classmethod
    def update_attribute( cls,
                          attribute: EntityAttribute,
                          hb_field: dict,
                          order_id: int,
                          message_list: List[str],
                          updated_prefix: str ):
        was_changed = HbImporter.update_attribute_from_hb_field(
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

    @classmethod
    def remove_attribute( cls,
                          attribute: EntityAttribute,
                          message_list: List[str] ):
        # Hard-delete: these are integration-owned attributes (not
        # editable by the user), so the SoftDeleteAttributeModel's
        # default soft-delete + restore affordance doesn't apply.
        # Soft-deleting would surface the row under "Deleted
        # Attributes" with a restore button, and a restore creates
        # an inconsistency between HI and the integration's source
        # of truth.
        old_name = attribute.name
        attribute.delete( hard_delete = True )
        message_list.append( f'Field attribute removed: {old_name}' )
        return

    @classmethod
    def create_attachment_attribute( cls,
                                     entity: Entity,
                                     hb_attachment: dict,
                                     order_id: int ) -> EntityAttribute:
        return HbImporter.create_attribute_from_hb_attachment(
            entity = entity,
            hb_attachment = hb_attachment,
            order_id = order_id,
        )

    @classmethod
    def update_attachment_attribute( cls,
                                     attribute: EntityAttribute,
                                     hb_attachment: dict,
                                     order_id: int,
                                     message_list: List[str],
                                     updated_prefix: str ):
        was_changed = HbImporter.update_attribute_from_hb_attachment(
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

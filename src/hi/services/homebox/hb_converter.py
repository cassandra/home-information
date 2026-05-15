from typing import Dict, List, Optional
import mimetypes
import os

from django.db import transaction
from django.core.files.base import ContentFile

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.integrations.transient_models import IntegrationKey

from .hb_metadata import HbMetaData
from .hb_models import HbItem
import logging

logger = logging.getLogger(__name__)


class HbConverter:

    HB_ITEM_ATTRIBUTE_FIELD_MAP = [
        ( 'description', 'Description' ),
        ( 'serial_number', 'Serial Number' ),
        ( 'model_number', 'Model Number' ),
        ( 'manufacturer', 'Manufacturer' ),
    ]

    @classmethod
    def create_models_for_hb_item( cls,
                                   hb_item : HbItem,
                                   entity  : Optional[Entity] = None ) -> Entity:
        """
        Create or repopulate the integration-owned components for an
        HbItem. When ``entity`` is None (the standard import path), a
        fresh Entity is created from the upstream payload. When
        ``entity`` is provided (the auto-reconnect path from Issue
        #281), the integration-owned fields on that entity are
        repopulated; the entity's ``name`` is deliberately preserved
        because the user may have edited it before/after the
        intervening disconnect.
        """
        with transaction.atomic():
            entity_integration_key = cls.hb_item_to_integration_key( hb_item = hb_item )
            entity_payload = cls.hb_item_to_entity_payload( hb_item = hb_item )

            if entity is None:
                entity = Entity(
                    name = cls.hb_item_to_entity_name( hb_item = hb_item ),
                    entity_type_str = str( cls.hb_item_to_entity_type( hb_item = hb_item ) ),
                )

            # The fields below apply equally to fresh-create and
            # reconnect: integration_key, integration_payload, and the
            # integration-managed access flags are all integration-owned
            # and must reflect the current upstream state. The entity
            # name and entity_type are intentionally left alone on the
            # reconnect path (set above only for fresh-create).
            entity.integration_key = entity_integration_key
            entity.integration_payload = entity_payload
            entity.can_user_delete = HbMetaData.allow_entity_deletion
            entity.can_add_custom_attributes = HbMetaData.can_add_custom_attributes
            entity.save()

        return entity

    @classmethod
    def update_models_for_hb_item( cls, entity : Entity, hb_item ) -> List[str]:
        messages = list()

        with transaction.atomic():
            entity_name = cls.hb_item_to_entity_name( hb_item = hb_item )
            if entity.name != entity_name:
                messages.append( f'Name changed for {entity}. Setting to "{entity_name}"' )
                entity.name = entity_name

            desired_entity_type = cls.hb_item_to_entity_type( hb_item = hb_item )
            if entity.entity_type != desired_entity_type:
                messages.append( f'Entity type changed for {entity}. Setting to "{desired_entity_type}"' )
                entity.entity_type = desired_entity_type

            if entity.can_add_custom_attributes != HbMetaData.can_add_custom_attributes:
                messages.append( f'can_add_custom_attributes changed for {entity}.' )
                entity.can_add_custom_attributes = HbMetaData.can_add_custom_attributes

            new_payload = cls.hb_item_to_entity_payload( hb_item = hb_item )
            if entity.integration_payload != new_payload:
                entity.integration_payload = new_payload
                messages.append( f'Integration payload updated for {entity}.' )

            if messages:
                entity.save()

        return messages

    @classmethod
    def hb_item_to_integration_key( cls, hb_item: HbItem ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = HbMetaData.integration_id,
            integration_name = str( hb_item.id ),
        )

    @classmethod
    def hb_field_to_integration_key( cls, hb_field: Dict ) -> IntegrationKey:
        field_id = str(hb_field.get('id', '')).strip()
        if not field_id:
            logger.error(
                'Field id is missing for HomeBox field with name '
                f'{hb_field.get("name", "")}. Cannot create integration key.'
            )
            return None
        
        return IntegrationKey(
            integration_id = HbMetaData.integration_id,
            integration_name = f'field:{field_id}',
        )

    @classmethod
    def hb_item_to_entity_name( cls, hb_item: HbItem ) -> str:
        item_name = hb_item.name

        if not item_name:
            logger.error(f'Item name is missing for HomeBox item with id {hb_item.id}. Using default name.' )
            return f'HomeBox Item {hb_item.id}'
        
        return item_name

    @classmethod
    def hb_item_to_entity_type( cls, hb_item: HbItem ) -> EntityType:
        return EntityType.OTHER

    @classmethod
    def hb_item_to_entity_payload( cls, hb_item: HbItem ) -> Dict:
        # Timestamps (createdAt / updatedAt) are deliberately excluded.
        # They are metadata about *when* a change happened, not the
        # content of the change — and real HomeBox can tick updatedAt
        # for housekeeping events (label re-associations, internal
        # caches) the operator doesn't care about. Including them
        # would make payload-equality change detection report
        # spurious updates on every refresh.
        payload: Dict = {
            'quantity': hb_item.quantity,
            'insured': hb_item.insured,
            'archived': hb_item.archived,
            'purchase_price': hb_item.purchase_price,
            'asset_id': hb_item.asset_id,
            'sync_child_items_locations': hb_item.sync_child_items_locations,
            'lifetime_warranty': hb_item.lifetime_warranty,
            'warranty_expires': hb_item.warranty_expires,
            'warranty_details': hb_item.warranty_details,
            'purchase_time': hb_item.purchase_time,
            'purchase_from': hb_item.purchase_from,
            'sold_time': hb_item.sold_time,
            'sold_to': hb_item.sold_to,
            'sold_price': hb_item.sold_price,
            'sold_notes': hb_item.sold_notes,
            'notes': hb_item.notes,
        }

        location = hb_item.location
        if location is None:
            logger.warning( f'HomeBox item {hb_item.id} missing location dict' )
            payload['location'] = None
        else:
            payload['location'] = {
                'id': location.get( 'id' ),
                'name': location.get( 'name' ),
                'description': location.get( 'description' ),
                'createdAt': location.get( 'createdAt' ),
                'updatedAt': location.get( 'updatedAt' ),
            }

        labels = hb_item.labels
        if labels is None:
            logger.warning( f'HomeBox item {hb_item.id} missing labels list' )
            payload['labels'] = []
        else:
            normalized_labels: List[Dict] = []
            for label in labels:
                if not isinstance( label, dict ):
                    continue
                normalized_labels.append({
                    'id': label.get( 'id' ),
                    'name': label.get( 'name' ),
                    'description': label.get( 'description' ),
                    'color': label.get( 'color' ),
                    'created_at': label.get( 'createdAt' ),
                    'updated_at': label.get( 'updatedAt' ),
                })
            payload['labels'] = normalized_labels

        return payload

    @classmethod
    def hb_field_to_attribute_name( cls, hb_field: Dict ) -> str:
        return str(hb_field.get('name', '')).strip()

    @classmethod
    def _hb_item_to_field_list( cls, hb_item: HbItem ) -> List[Dict]:
        hb_field_list = list( hb_item.fields )

        for key, name in cls.HB_ITEM_ATTRIBUTE_FIELD_MAP:
            value = str( getattr( hb_item, key, '' ) or '' ).strip()
            if not value:
                continue

            hb_field_list.append({
                'id': f'hb_item:{key}',
                'type': 'text',  # all HomeBox-created fields are text, even for numbers/booleans
                'name': name,
                'textValue': value,
                'numberValue': None,
                'booleanValue': None,
            })

        return hb_field_list

    @classmethod
    def hb_item_to_attribute_field_list( cls, hb_item: HbItem ) -> List[Dict]:
        """Returns only normal (non-attachment) attribute fields from HomeBox item."""
        return cls._hb_item_to_field_list( hb_item = hb_item )

    @classmethod
    def hb_attachment_to_filename( cls, hb_attachment: Dict, mime_type: str = '' ) -> str:
        title = str( hb_attachment.get( 'title', '' ) or '' ).strip()
        if title:
            filename = os.path.basename( title )
        else:
            attachment_id = str( hb_attachment.get( 'id', '' ) or '' ).strip() or 'attachment'
            filename = attachment_id

        if '.' in filename:
            return filename

        guessed_extension = ''
        normalized_mime_type = str( mime_type or '' ).split(';')[0].strip()
        if normalized_mime_type:
            guessed_extension = mimetypes.guess_extension( normalized_mime_type ) or ''

        if guessed_extension:
            return f'{filename}{guessed_extension}'
        return filename

    @classmethod
    def hb_item_to_attachment_field_list( cls, hb_item: HbItem ) -> List[Dict]:
        attachment_list = []

        if not getattr( hb_item, 'client', None ):
            logger.warning( f'HomeBox item {hb_item.id} has no client; cannot download attachments' )
            return attachment_list

        for attachment in list( hb_item.attachments or [] ):
            if not isinstance( attachment, dict ):
                continue

            attachment_id = str( attachment.get( 'id', '' ) or '' ).strip()
            if not attachment_id:
                continue

            attachment_title = (
                str( attachment.get( 'title', '' ) or '' ).strip()
                or f'Attachment {attachment_id}'
            )
            attachment_mime_type = str( attachment.get( 'mimeType', '' ) or '' ).strip()

            downloaded_attachment = None
            try:
                downloaded_attachment = hb_item.client.download_attachment(
                    item_id = hb_item.id,
                    attachment_id = attachment_id,
                )
            except Exception as e:
                logger.warning(
                    'Unable to download HomeBox attachment '
                    f'{attachment_id} for item {hb_item.id}: {e}'
                )
                continue

            if not downloaded_attachment:
                logger.warning(
                    'Missing downloaded content for HomeBox attachment '
                    f'{attachment_id} (item {hb_item.id}); skipping attachment'
                )
                continue

            attachment_list.append({
                'id': f'attachment:{attachment_id}',
                'type': 'attachment',
                'name': attachment_title,
                'textValue': attachment_title,
                'numberValue': None,
                'booleanValue': None,
                'mimeType': attachment_mime_type,
                'attachment': attachment,
                'downloaded_attachment': downloaded_attachment,
            })

        return attachment_list

    @classmethod
    def hb_attachment_to_attribute_name( cls, hb_attachment: Dict ) -> str:
        return str(hb_attachment.get('name', '')).strip()

    @classmethod
    def hb_attachment_to_integration_key( cls, hb_attachment: Dict ) -> IntegrationKey:
        return cls.hb_field_to_integration_key( hb_field = hb_attachment )

    @classmethod
    def hb_field_to_attribute_payload( cls, hb_field: Dict, order_id: int ) -> Optional[Dict]:
        if not isinstance( hb_field, dict ):
            return None

        hb_field_type = str( hb_field.get( 'type', '' ) or '' ).strip().lower()

        if hb_field_type == 'attachment':
            return cls.hb_attachment_to_attribute_payload(
                hb_attachment = hb_field,
                order_id = order_id,
            )

        integration_key = cls.hb_field_to_integration_key( hb_field = hb_field )
        if not integration_key:
            logger.warning( 'HomeBox field missing integration key; skipping attribute payload' )
            return None

        return {
            'name': cls.hb_field_to_attribute_name( hb_field = hb_field ),
            'value': hb_field.get('textValue', ''),
            'value_type_str': str(AttributeValueType.TEXT),
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'is_editable': False,
            'is_required': False,
            'order_id': order_id,
            'integration_key_str': str( integration_key ),
        }

    @classmethod
    def hb_attachment_to_attribute_payload( cls, hb_attachment: Dict, order_id: int ) -> Optional[Dict]:
        if not isinstance( hb_attachment, dict ):
            return None

        downloaded_attachment = hb_attachment.get( 'downloaded_attachment' )
        if not downloaded_attachment or not isinstance( downloaded_attachment, dict ):
            logger.warning(
                'HomeBox attachment payload missing downloaded_attachment; '
                'skipping attribute creation'
            )
            return None

        raw_content = downloaded_attachment.get( 'content' )
        if not raw_content:
            logger.warning('HomeBox attachment payload missing content; skipping attribute creation')
            return None

        mime_type = str( downloaded_attachment.get( 'mime_type', '' ) ).strip()
        if not mime_type:
            logger.warning('HomeBox attachment payload missing mime_type; skipping attribute creation')
            return None

        attachment_info = hb_attachment.get( 'attachment' )
        if not attachment_info or not isinstance( attachment_info, dict ):
            logger.warning('HomeBox attachment payload missing attachment info; skipping attribute creation')
            return None

        integration_key = cls.hb_attachment_to_integration_key( hb_attachment = hb_attachment )
        if not integration_key:
            logger.warning( 'HomeBox attachment missing integration key; skipping attribute creation' )
            return None

        filename = cls.hb_attachment_to_filename(
            hb_attachment = attachment_info,
            mime_type = mime_type,
        )

        payload = {
            'name': cls.hb_attachment_to_attribute_name( hb_attachment = hb_attachment ),
            'value': hb_attachment.get('textValue', ''),
            'value_type_str': str(AttributeValueType.FILE),
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'is_editable': False,
            'is_required': False,
            'order_id': order_id,
            'integration_key_str': str( integration_key ),
            'file_mime_type': mime_type if mime_type else None,
        }

        payload['file_value'] = ContentFile( raw_content, name = filename )

        return payload

    @classmethod
    def create_attribute_from_hb_field( cls,
                                        entity: Entity,
                                        hb_field: Dict,
                                        order_id: int ) -> Optional[EntityAttribute]:
        payload = cls.hb_field_to_attribute_payload(
            hb_field = hb_field,
            order_id = order_id,
        )
        if not payload:
            return None

        return EntityAttribute.objects.create(
            entity = entity,
            **payload,
        )

    @classmethod
    def update_attribute_from_hb_field( cls,
                                        attribute: EntityAttribute,
                                        hb_field: Dict,
                                        order_id: int ) -> bool:
        payload = cls.hb_field_to_attribute_payload(
            hb_field = hb_field,
            order_id = order_id,
        )
        if not payload:
            return False

        incoming_file = payload.pop( 'file_value', None )

        was_changed = False
        for field_name, field_value in payload.items():
            if getattr( attribute, field_name ) != field_value:
                setattr( attribute, field_name, field_value )
                was_changed = True

        # Only update file content when needed; this avoids rewriting the same file on each sync.
        if incoming_file and not attribute.file_value:
            attribute.file_value = incoming_file
            was_changed = True

        if was_changed:
            attribute.save()

        return was_changed

    @classmethod
    def create_attribute_from_hb_attachment( cls,
                                             entity: Entity,
                                             hb_attachment: Dict,
                                             order_id: int ) -> Optional[EntityAttribute]:
        payload = cls.hb_attachment_to_attribute_payload(
            hb_attachment = hb_attachment,
            order_id = order_id,
        )
        if not payload:
            return None

        return EntityAttribute.objects.create(
            entity = entity,
            **payload,
        )

    @classmethod
    def update_attribute_from_hb_attachment( cls,
                                             attribute: EntityAttribute,
                                             hb_attachment: Dict,
                                             order_id: int ) -> bool:
        payload = cls.hb_attachment_to_attribute_payload(
            hb_attachment = hb_attachment,
            order_id = order_id,
        )
        if not payload:
            return False

        incoming_file = payload.pop( 'file_value', None )

        was_changed = False
        for field_name, field_value in payload.items():
            if getattr( attribute, field_name ) != field_value:
                setattr( attribute, field_name, field_value )
                was_changed = True

        if incoming_file and not attribute.file_value:
            attribute.file_value = incoming_file
            was_changed = True

        if was_changed:
            attribute.save()

        return was_changed

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
from .hb_client.helpers.item import HbItem
from .hb_client.helpers import globals as g


class HbConverter:

    HB_ITEM_ATTRIBUTE_FIELD_MAP = [
        ( 'description', 'Description' ),
        ( 'serial_number', 'Serial Number' ),
        ( 'model_number', 'Model Number' ),
        ( 'manufacturer', 'Manufacturer' ),
    ]

    @classmethod
    def create_models_for_hb_item( cls, hb_item: HbItem ) -> Entity:

        with transaction.atomic():
            entity_integration_key = cls.hb_item_to_integration_key( hb_item = hb_item )
            entity_name = cls.hb_item_to_entity_name( hb_item = hb_item )
            entity_type = cls.hb_item_to_entity_type( hb_item = hb_item )
            
            entity = Entity(
                name = entity_name,
                entity_type_str = str(entity_type),
                can_user_delete = HbMetaData.allow_entity_deletion,
                can_add_custom_attributes = HbMetaData.can_add_custom_attributes,
            )

            entity.integration_key = entity_integration_key
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
            g.logger.Error(f'Field id is missing for HomeBox field with name {hb_field.get("name", "")}. Cannot create integration key.' )
            return None
        
        return IntegrationKey(
            integration_id = HbMetaData.integration_id,
            integration_name = f'field:{field_id}',
        )

    @classmethod
    def hb_item_to_entity_name( cls, hb_item: HbItem ) -> str:
        item_name = hb_item.name

        if not item_name:
            g.logger.Error(f'Item name is missing for HomeBox item with id {hb_item.id}. Using default name.' )
            return f'HomeBox Item {hb_item.id}'
        
        return item_name

    @classmethod
    def hb_item_to_entity_type( cls, hb_item: HbItem ) -> EntityType:
        return EntityType.OTHER

    @classmethod
    def _create_entity_attributes_from_hb_fields( cls, entity: Entity, hb_item: HbItem ):
        hb_item_fields = hb_item.fields

        for order_id, hb_field in enumerate( hb_item_fields ):
            cls.create_attribute_from_hb_field(
                entity = entity,
                hb_field = hb_field,
                order_id = order_id,
            )

    @classmethod
    def hb_field_to_attribute_name( cls, hb_field: Dict ) -> str:
        return str(hb_field.get('name', '')).strip()

    @classmethod
    def hb_item_to_hb_field_list ( cls, hb_item: HbItem ) -> List[Dict]:
        hb_field_list = list( hb_item.fields )

        for key, name in cls.HB_ITEM_ATTRIBUTE_FIELD_MAP:
            value = str( getattr( hb_item, key, '' ) or '' ).strip()
            if not value:
                continue

            hb_field_list.append({
                'id': f'hb_item:{key}',
                'type': 'text', # all fields created in homebox are text type, even if they represent numbers or booleans
                'name': name,
                'textValue': value,
                'numberValue': None,
                'booleanValue': None,
            })

        return hb_field_list

    @classmethod
    def hb_item_to_attribute_field_list( cls, hb_item: HbItem ) -> List[Dict]:
        """Returns only normal (non-attachment) attribute fields from HomeBox item."""
        return cls.hb_item_to_hb_field_list( hb_item = hb_item )

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
    def hb_item_to_attachment_list( cls, hb_item: HbItem ) -> List[Dict]:
        attachment_list = []

        for attachment in list( hb_item.attachments or [] ):
            if not isinstance( attachment, dict ):
                continue

            attachment_id = str( attachment.get( 'id', '' ) or '' ).strip()
            if not attachment_id:
                continue

            attachment_title = str( attachment.get( 'title', '' ) or '' ).strip() or f'Attachment {attachment_id}'
            attachment_mime_type = str( attachment.get( 'mimeType', '' ) or '' ).strip()

            downloaded_attachment = None
            try:
                downloaded_attachment = hb_item.download_attachment( attachment = attachment )
            except Exception as e:
                g.logger.Debug(1, f'Unable to download HomeBox attachment {attachment_id}: {e}')

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
    def hb_item_to_attachment_field_list( cls, hb_item: HbItem ) -> List[Dict]:
        """Backward-compatible alias for callers/tests using old naming."""
        return cls.hb_item_to_attachment_list( hb_item = hb_item )

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

        return {
            'name': cls.hb_field_to_attribute_name( hb_field = hb_field ),
            'value': hb_field.get('textValue', ''),
            'value_type_str': str(AttributeValueType.TEXT),
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'is_editable': False,
            'is_required': False,
            'order_id': order_id,
            'integration_key_str': cls.hb_field_to_integration_key( hb_field = hb_field ),
        }

    @classmethod
    def hb_attachment_to_attribute_payload( cls, hb_attachment: Dict, order_id: int ) -> Optional[Dict]:
        if not isinstance( hb_attachment, dict ):
            return None

        downloaded_attachment = hb_attachment.get( 'downloaded_attachment' ) or {}
        raw_content = downloaded_attachment.get( 'content' )

        mime_type = str(
            downloaded_attachment.get( 'mime_type', '' )
            or hb_attachment.get( 'mimeType', '' )
            or ''
        ).strip()

        attachment_info = hb_attachment.get( 'attachment' ) or {}
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
            'integration_key_str': cls.hb_attachment_to_integration_key( hb_attachment = hb_attachment ),
            'file_mime_type': mime_type or None,
        }

        if raw_content:
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

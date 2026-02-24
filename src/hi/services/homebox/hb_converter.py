from typing import Dict, List, Optional

from django.db import transaction

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
    def hb_field_to_attribute_payload( cls, hb_field: Dict, order_id: int ) -> Optional[Dict]:
        if not isinstance( hb_field, dict ):
            return None

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

        was_changed = False
        for field_name, field_value in payload.items():
            if getattr( attribute, field_name ) != field_value:
                setattr( attribute, field_name, field_value )
                was_changed = True

        if was_changed:
            attribute.save()

        return was_changed

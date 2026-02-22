from typing import Dict, List

from django.db import transaction

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.integrations.transient_models import IntegrationKey

from .hb_metadata import HbMetaData
from .hb_client.helpers.item import Item
from .hb_client.helpers import globals as g


class HbConverter:

    @classmethod
    def create_models_for_hb_item( cls, hb_item: Item ) -> Entity:

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
            cls._create_entity_attributes_from_hb_fields(
                entity = entity,
                hb_item = hb_item,
            )
            
        return entity

    @classmethod
    def update_models_for_hb_item( cls, entity : Entity, hb_item ) -> List[str]:
        messages = list()

        with transaction.atomic():
            entity_name = cls.hb_item_to_entity_name( hb_item = hb_item )
            if entity.name != entity_name:
                messages.append( f'Name changed for {entity}. Setting to "{entity_name}"' )
                entity.name = entity_name

            attr_messages = cls._update_entity_attributes_from_hb_fields(
                entity = entity,
                hb_item = hb_item,
            )
            messages.extend( attr_messages )

            if messages:
                entity.save()

        return messages

    @classmethod
    def hb_item_to_integration_key( cls, hb_item: Item ) -> IntegrationKey:
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
    def hb_item_to_entity_name( cls, hb_item: Item) -> str:
        item_name = hb_item.name

        if not item_name:
            g.logger.Error(f'Item name is missing for HomeBox item with id {hb_item.id}. Using default name.' )
            return f'HomeBox Item {hb_item.id}'
        
        return item_name

    @classmethod
    def hb_item_to_entity_type( cls, hb_item: Item ) -> EntityType:
        return EntityType.OTHER

    @classmethod
    def _create_entity_attributes_from_hb_fields( cls, entity: Entity, hb_item: Item ):
        hb_item_fields = hb_item.fields

        for order_id, hb_field in enumerate( hb_item_fields ):
            if not isinstance( hb_field, dict ):
                continue

            field_name = str(hb_field.get('name', '')).strip()
            text_value = hb_field.get('textValue', '')
            value_type = AttributeValueType.TEXT

            field_key = cls.hb_field_to_integration_key( hb_field = hb_field )

            EntityAttribute.objects.create(
                entity = entity,
                name = field_name,
                value = text_value,
                value_type_str = str(value_type),
                attribute_type_str = str(AttributeType.PREDEFINED),
                is_editable = False,
                is_required = False,
                order_id = order_id,
                integration_key_str = str(field_key),
            )

    @classmethod
    def _update_entity_attributes_from_hb_fields( cls, entity: Entity, hb_item: Item ) -> List[str]:
        hb_item_fields = hb_item.fields
        messages = list()

        existing_attrs = list(entity.attributes.all())
        existing_by_key = {
            attr.integration_key_str: attr
            for attr in existing_attrs
            if attr.integration_key_str and attr.integration_key_str.startswith(f'{HbMetaData.integration_id}.field:')
        }
        fallback_by_name = {
            attr.name: attr
            for attr in existing_attrs
            if ((not attr.integration_key_str)
                and (attr.attribute_type == AttributeType.PREDEFINED)
                and (not attr.is_editable))
        }
        seen_field_key_set = set()

        for order_id, hb_field in enumerate( hb_item_fields ):
            if not isinstance( hb_field, dict ):
                continue

            field_key = cls.hb_field_to_integration_key( hb_field = hb_field )

            field_name = str(hb_field.get('name', '')).strip()
            text_value = hb_field.get( 'textValue', '' )
            value_type = AttributeValueType.TEXT

            attribute = None
            if field_key:
                seen_field_key_set.add( field_key )
                attribute = existing_by_key.get( field_key )

            if not attribute:
                attribute = fallback_by_name.get( field_name )

            if attribute:
                was_changed = False
                if attribute.name != field_name:
                    attribute.name = field_name
                    was_changed = True
                if attribute.value != text_value:
                    attribute.value = text_value
                    was_changed = True
                if attribute.value_type_str != str(value_type):
                    attribute.value_type_str = str(value_type)
                    was_changed = True
                if attribute.attribute_type_str != str(AttributeType.PREDEFINED):
                    attribute.attribute_type_str = str(AttributeType.PREDEFINED)
                    was_changed = True
                if attribute.is_editable:
                    attribute.is_editable = False
                    was_changed = True
                if attribute.is_required:
                    attribute.is_required = False
                    was_changed = True
                if attribute.order_id != order_id:
                    attribute.order_id = order_id
                    was_changed = True
                if field_key and attribute.integration_key_str != field_key:
                    attribute.integration_key_str = field_key
                    was_changed = True

                if was_changed:
                    attribute.save()
                    messages.append( f'Field attribute updated: {field_name}' )
                continue

            EntityAttribute.objects.create(
                entity = entity,
                name = field_name,
                value = text_value,
                value_type_str = str(value_type),
                attribute_type_str = str(AttributeType.PREDEFINED),
                is_editable = False,
                is_required = False,
                order_id = order_id,
                integration_key_str = str(field_key),
            )
            messages.append( f'Field attribute added: {field_name}' )

        for existing_key, attribute in existing_by_key.items():
            if existing_key not in seen_field_key_set:
                old_name = attribute.name
                attribute.delete()
                messages.append( f'Field attribute removed: {old_name}' )

        return messages

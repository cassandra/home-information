from typing import Dict, List, Optional
import logging

from django.db import transaction

from hi.apps.entity.models import Entity, EntityAttribute

from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.shared.hb_converter import HbConverter
from hi.services.homebox.shared.hb_models import HbItem

logger = logging.getLogger(__name__)


class HbImporter:

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
            entity_integration_key = HbConverter.hb_item_to_integration_key( hb_item = hb_item )
            entity_payload = HbConverter.hb_item_to_entity_payload( hb_item = hb_item )

            if entity is None:
                entity = Entity(
                    name = HbConverter.hb_item_to_entity_name( hb_item = hb_item ),
                    entity_type_str = str( HbConverter.hb_item_to_entity_type( hb_item = hb_item ) ),
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
            entity.allow_internal_attributes = HbMetaData.allow_internal_attributes
            entity.save()

        return entity

    @classmethod
    def update_models_for_hb_item( cls, entity : Entity, hb_item ) -> List[str]:
        messages = list()

        with transaction.atomic():
            entity_name = HbConverter.hb_item_to_entity_name( hb_item = hb_item )
            if entity.name != entity_name:
                messages.append( f'Name changed for {entity}. Setting to "{entity_name}"' )
                entity.name = entity_name

            desired_entity_type = HbConverter.hb_item_to_entity_type( hb_item = hb_item )
            if entity.entity_type != desired_entity_type:
                messages.append( f'Entity type changed for {entity}. Setting to "{desired_entity_type}"' )
                entity.entity_type = desired_entity_type

            if entity.allow_internal_attributes != HbMetaData.allow_internal_attributes:
                messages.append( f'allow_internal_attributes changed for {entity}.' )
                entity.allow_internal_attributes = HbMetaData.allow_internal_attributes

            new_payload = HbConverter.hb_item_to_entity_payload( hb_item = hb_item )
            if entity.integration_payload != new_payload:
                entity.integration_payload = new_payload
                messages.append( f'Integration payload updated for {entity}.' )

            if messages:
                entity.save()

        return messages

    @classmethod
    def create_attribute_from_hb_field( cls,
                                        entity: Entity,
                                        hb_field: Dict,
                                        order_id: int ) -> Optional[EntityAttribute]:
        payload = HbConverter.hb_field_to_attribute_payload(
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
        payload = HbConverter.hb_field_to_attribute_payload(
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
        payload = HbConverter.hb_attachment_to_attribute_payload(
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
        payload = HbConverter.hb_attachment_to_attribute_payload(
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

"""HomeBox attribute-population for the IMPORT capability.

Exercised by ``HomeBoxImporter.run_import`` via
``populate_attributes_for_imported_entity``. Creates user-owned
(CUSTOM) EntityAttribute rows so the operator can freely edit the
imported data after it lands in HI."""
from typing import Dict, Optional
import logging

from hi.apps.entity.models import Entity, EntityAttribute

from hi.services.homebox.hb_converter import HbConverter

logger = logging.getLogger(__name__)


def populate_attributes_for_imported_entity( entity : Entity, hb_item ) -> None:
    """Create user-owned EntityAttribute rows from HomeBox fields and
    attachments. Called once per item at import time inside the
    entity's transaction."""
    hb_field_list = HbConverter.hb_item_to_attribute_field_list( hb_item = hb_item )
    for order_id, hb_field in enumerate( hb_field_list ):
        HbImporter.create_attribute_from_hb_field(
            entity = entity,
            hb_field = hb_field,
            order_id = order_id,
        )
    attachment_list = HbConverter.hb_item_to_attachment_field_list( hb_item = hb_item )
    start_order = len( hb_field_list )
    for order_id, hb_attachment in enumerate( attachment_list, start = start_order ):
        HbImporter.create_attribute_from_hb_attachment(
            entity = entity,
            hb_attachment = hb_attachment,
            order_id = order_id,
        )


class HbImporter:

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

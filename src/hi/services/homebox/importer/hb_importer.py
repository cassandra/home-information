"""HomeBox attribute-population classmethods. Dormant — these are
called only from the preserved attribute-sync helpers in
hb_attribute_sync.py. #358's Importer will exercise them via the
Importer protocol."""
from typing import Dict, Optional
import logging

from hi.apps.entity.models import Entity, EntityAttribute

from hi.services.homebox.shared.hb_converter import HbConverter

logger = logging.getLogger(__name__)


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

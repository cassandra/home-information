from typing import Dict, List, Optional
import mimetypes
import os
import re

from django.core.files.base import ContentFile

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.integrations.transient_models import IntegrationKey

from hi.services.homebox.hb_metadata import HbMetaData
from .hb_models import HbItem
import logging

logger = logging.getLogger(__name__)


# Canonical mapping of HbItem properties to user-visible labels. Shared
# by the Connect-mode resolver (live read-only display) and the
# importer's synthetic-field generation so both surfaces expose the
# same set of HomeBox item metadata.
# (HbItem property, display label)
HB_ITEM_FIELD_PAIRS = [
    ( 'description', 'Description' ),
    ( 'manufacturer', 'Manufacturer' ),
    ( 'model_number', 'Model Number' ),
    ( 'serial_number', 'Serial Number' ),
    ( 'asset_id', 'Asset ID' ),
    ( 'purchase_from', 'Purchased From' ),
    ( 'purchase_time', 'Purchase Date' ),
    ( 'warranty_details', 'Warranty Details' ),
    ( 'warranty_expires', 'Warranty Expires' ),
    ( 'notes', 'Notes' ),
]


# Keyword → EntityType map for heuristic type assignment of HomeBox
# items. Authoring order does not matter — ``_KEYWORD_PATTERNS`` below
# pre-sorts by specificity (word count descending, then char length
# descending, then alphabetical). Multi-word keywords always win over
# single-word matches; longer keywords win over shorter at equal word
# count.
#
# Add keywords liberally as real-world data accumulates. The
# false-positive risk is small as long as keywords are nouns naming
# the kind of thing (not adjectives or verbs).
HB_KEYWORD_ENTITY_TYPE_MAP = [
    # Multi-word patterns.
    ( 'access point', EntityType.ACCESS_POINT ),
    ( 'attic stairs', EntityType.ATTIC_STAIRS ),
    ( 'av receiver', EntityType.AV_RECEIVER ),
    ( 'battery storage', EntityType.BATTERY_STORAGE ),
    ( 'carbon monoxide', EntityType.CARBON_MONOXIDE_DETECTOR ),
    ( 'ceiling fan', EntityType.CEILING_FAN ),
    ( 'clothes dryer', EntityType.CLOTHES_DRYER ),
    ( 'clothes washer', EntityType.CLOTHES_WASHER ),
    ( 'coffee machine', EntityType.COFFEE_MAKER ),
    ( 'coffee maker', EntityType.COFFEE_MAKER ),
    ( 'door lock', EntityType.DOOR_LOCK ),
    ( 'electric meter', EntityType.ELECTRICITY_METER ),
    ( 'electric panel', EntityType.ELECTRIC_PANEL ),
    ( 'electrical outlet', EntityType.ELECTRICAL_OUTLET ),
    ( 'ev charger', EntityType.EV_CHARGER ),
    ( 'exhaust fan', EntityType.EXHAUST_FAN ),
    ( 'fire extinguisher', EntityType.FIRE_EXTINGUISHER ),
    ( 'garage door', EntityType.GARAGE_DOOR ),
    ( 'garbage disposal', EntityType.GARBAGE_DISPOSAL ),
    ( 'gas detector', EntityType.GAS_DETECTOR ),
    ( 'gas meter', EntityType.GAS_METER ),
    ( 'hedge trimmer', EntityType.HEDGE_TRIMMER ),
    ( 'lawn mower', EntityType.LAWN_MOWER ),
    ( 'leaf blower', EntityType.LEAF_BLOWER ),
    ( 'microwave oven', EntityType.MICROWAVE_OVEN ),
    ( 'motion sensor', EntityType.MOTION_SENSOR ),
    ( 'network switch', EntityType.NETWORK_SWITCH ),
    ( 'pool filter', EntityType.POOL_FILTER ),
    ( 'pool heater', EntityType.POOL_HEATER ),
    ( 'pool pump', EntityType.POOL_PUMP ),
    ( 'power washer', EntityType.POWER_WASHER ),
    ( 'pressure washer', EntityType.POWER_WASHER ),
    ( 'radon detector', EntityType.RADON_DETECTOR ),
    ( 'range hood', EntityType.RANGE_HOOD ),
    ( 'satellite dish', EntityType.SATELLITE_DISH ),
    ( 'smoke detector', EntityType.SMOKE_DETECTOR ),
    ( 'solar panel', EntityType.SOLAR_PANEL ),
    ( 'sump pump', EntityType.SUMP_PUMP ),
    ( 'wall switch', EntityType.WALL_SWITCH ),
    ( 'water filter', EntityType.WATER_FILTER ),
    ( 'water heater', EntityType.WATER_HEATER ),
    ( 'water meter', EntityType.WATER_METER ),
    ( 'water softener', EntityType.WATER_SOFTENER ),
    ( 'weather station', EntityType.WEATHER_STATION ),
    # Single-word patterns. Tools.
    ( 'drill', EntityType.TOOL ),
    ( 'hammer', EntityType.TOOL ),
    ( 'pliers', EntityType.TOOL ),
    ( 'sander', EntityType.TOOL ),
    ( 'saw', EntityType.TOOL ),
    ( 'screwdriver', EntityType.TOOL ),
    ( 'wrench', EntityType.TOOL ),
    # Lighting.
    ( 'bulb', EntityType.LIGHT ),
    ( 'chandelier', EntityType.LIGHT ),
    ( 'lamp', EntityType.LIGHT ),
    ( 'light', EntityType.LIGHT ),
    ( 'sconce', EntityType.LIGHT ),
    # Computer / network.
    ( 'computer', EntityType.COMPUTER ),
    ( 'desktop', EntityType.COMPUTER ),
    ( 'laptop', EntityType.COMPUTER ),
    ( 'modem', EntityType.MODEM ),
    ( 'printer', EntityType.PRINTER ),
    ( 'router', EntityType.NETWORK_SWITCH ),
    ( 'server', EntityType.SERVER ),
    ( 'ups', EntityType.UPS ),
    # Audio / visual.
    ( 'receiver', EntityType.AV_RECEIVER ),
    ( 'soundbar', EntityType.SPEAKER ),
    ( 'speaker', EntityType.SPEAKER ),
    ( 'television', EntityType.TELEVISION ),
    ( 'tv', EntityType.TELEVISION ),
    # Appliances.
    ( 'dishwasher', EntityType.DISHWASHER ),
    ( 'dryer', EntityType.CLOTHES_DRYER ),
    ( 'freezer', EntityType.FREEZER ),
    ( 'fridge', EntityType.REFRIGERATOR ),
    ( 'grill', EntityType.GRILL ),
    ( 'microwave', EntityType.MICROWAVE_OVEN ),
    ( 'oven', EntityType.OVEN ),
    ( 'refrigerator', EntityType.REFRIGERATOR ),
    ( 'washer', EntityType.CLOTHES_WASHER ),
    # Climate.
    ( 'barometer', EntityType.BAROMETER ),
    ( 'humidifier', EntityType.HUMIDIFIER ),
    ( 'hygrometer', EntityType.HYGROMETER ),
    ( 'thermometer', EntityType.THERMOMETER ),
    ( 'thermostat', EntityType.THERMOSTAT ),
    # Outdoor.
    ( 'blower', EntityType.LEAF_BLOWER ),
    ( 'generator', EntityType.GENERATOR ),
    ( 'inverter', EntityType.INVERTER ),
    ( 'mower', EntityType.LAWN_MOWER ),
    ( 'trimmer', EntityType.TRIMMER ),
    # Security / cameras.
    ( 'camera', EntityType.CAMERA ),
    ( 'doorbell', EntityType.DOORBELL ),
    # Fixtures.
    ( 'bathtub', EntityType.BATHTUB ),
    ( 'shower', EntityType.SHOWER ),
    ( 'sink', EntityType.SINK ),
    ( 'toilet', EntityType.TOILET ),
]


# Fields scanned for keyword matches, in priority order. A match in
# an earlier-listed field wins over any match in a later field.
_TYPE_HEURISTIC_FIELDS = ( 'name', 'description' )


# Pre-sorted keyword patterns. Multi-word matches always beat
# single-word matches within the same field; longer keywords beat
# shorter at equal word count; alphabetical break for determinism.
_KEYWORD_PATTERNS = [
    (
        re.compile( rf'\b{re.escape(keyword)}\b', re.IGNORECASE ),
        entity_type,
    )
    for keyword, entity_type in sorted(
        HB_KEYWORD_ENTITY_TYPE_MAP,
        key = lambda pair: ( -len( pair[0].split() ), -len( pair[0] ), pair[0] ),
    )
]


class HbConverter:

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
        """Heuristic EntityType assignment for a HomeBox item.

        Two-pass priority:
          1. Field priority — ``name`` first, then ``description``.
             A match in name wins over any match in description.
             The user titled the item deliberately; the description
             is incidental commentary.
          2. Keyword specificity — within a field, longer / multi-
             word keyword matches beat shorter ones (handled by the
             pre-sort in ``_KEYWORD_PATTERNS``).

        Fallback: ``EntityType.OTHER`` when no keyword matches
        either field.
        """
        for field_name in _TYPE_HEURISTIC_FIELDS:
            field_value = getattr( hb_item, field_name, None )
            if not field_value:
                continue
            for pattern, entity_type in _KEYWORD_PATTERNS:
                if pattern.search( field_value ):
                    return entity_type
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

        tags = hb_item.tags
        if tags is None:
            logger.warning( f'HomeBox item {hb_item.id} missing tags list' )
            payload['tags'] = []
        else:
            normalized_tags: List[Dict] = []
            for tag in tags:
                if not isinstance( tag, dict ):
                    continue
                normalized_tags.append({
                    'id': tag.get( 'id' ),
                    'name': tag.get( 'name' ),
                    'description': tag.get( 'description' ),
                    'color': tag.get( 'color' ),
                    'created_at': tag.get( 'createdAt' ),
                    'updated_at': tag.get( 'updatedAt' ),
                })
            payload['tags'] = normalized_tags

        return payload

    @classmethod
    def hb_field_to_attribute_name( cls, hb_field: Dict ) -> str:
        return str(hb_field.get('name', '')).strip()

    @classmethod
    def _hb_item_to_field_list( cls, hb_item: HbItem ) -> List[Dict]:
        hb_field_list = list( hb_item.fields )

        for key, name in HB_ITEM_FIELD_PAIRS:
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
            'attribute_type_str': str(AttributeType.CUSTOM),
            'is_editable': True,
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
            'attribute_type_str': str(AttributeType.CUSTOM),
            'is_editable': True,
            'is_required': False,
            'order_id': order_id,
            'integration_key_str': str( integration_key ),
            'file_mime_type': mime_type if mime_type else None,
        }

        payload['file_value'] = ContentFile( raw_content, name = filename )

        return payload

from typing import Dict, List, Optional, TYPE_CHECKING, Any
from dataclasses import dataclass

if TYPE_CHECKING:
    from .hb_client import HbClient


class HbApi:
    """ Central place for translating HomeBox API response strings and internal variables. """

    ID_FIELD = 'id'
    NAME_FIELD = 'name'
    DESCRIPTION_FIELD = 'description'
    QUANTITY_FIELD = 'quantity'
    INSURED_FIELD = 'insured'
    ARCHIVED_FIELD = 'archived'
    CREATED_AT_FIELD = 'createdAt'
    UPDATED_AT_FIELD = 'updatedAt'
    PURCHASE_PRICE_FIELD = 'purchasePrice'
    ASSET_ID_FIELD = 'assetId'
    SYNC_CHILD_ITEMS_LOCATIONS_FIELD = 'syncChildItemsLocations'
    SERIAL_NUMBER_FIELD = 'serialNumber'
    MODEL_NUMBER_FIELD = 'modelNumber'
    MANUFACTURER_FIELD = 'manufacturer'
    LIFETIME_WARRANTY_FIELD = 'lifetimeWarranty'
    WARRANTY_EXPIRES_FIELD = 'warrantyExpires'
    WARRANTY_DETAILS_FIELD = 'warrantyDetails'
    PURCHASE_TIME_FIELD = 'purchaseTime'
    PURCHASE_FROM_FIELD = 'purchaseFrom'
    SOLD_TIME_FIELD = 'soldTime'
    SOLD_TO_FIELD = 'soldTo'
    SOLD_PRICE_FIELD = 'soldPrice'
    SOLD_NOTES_FIELD = 'soldNotes'
    NOTES_FIELD = 'notes'
    LOCATION_FIELD = 'location'
    LABELS_FIELD = 'labels'
    ATTACHMENTS_FIELD = 'attachments'
    FIELDS_FIELD = 'fields'


@dataclass
class HbItem:
    """ Wraps the JSON object from the API """

    api_dict: Dict[str, Any]
    client: Optional['HbClient'] = None

    @property
    def id(self) -> str:
        return self.api_dict.get(HbApi.ID_FIELD)

    @property
    def name(self) -> str:
        return self.api_dict.get(HbApi.NAME_FIELD, '')

    @property
    def description(self) -> str:
        return self.api_dict.get(HbApi.DESCRIPTION_FIELD, '')

    @property
    def quantity(self) -> Optional[int]:
        value = self.api_dict.get(HbApi.QUANTITY_FIELD)
        return value if isinstance(value, int) else None

    @property
    def insured(self) -> Optional[bool]:
        value = self.api_dict.get(HbApi.INSURED_FIELD)
        return value if isinstance(value, bool) else None

    @property
    def archived(self) -> Optional[bool]:
        value = self.api_dict.get(HbApi.ARCHIVED_FIELD)
        return value if isinstance(value, bool) else None

    @property
    def created_at(self) -> Optional[str]:
        value = self.api_dict.get(HbApi.CREATED_AT_FIELD)
        return value if isinstance(value, str) and value.strip() else None

    @property
    def updated_at(self) -> Optional[str]:
        value = self.api_dict.get(HbApi.UPDATED_AT_FIELD)
        return value if isinstance(value, str) and value.strip() else None

    @property
    def purchase_price(self) -> Optional[float]:
        value = self.api_dict.get(HbApi.PURCHASE_PRICE_FIELD)
        return value if isinstance(value, (int, float)) else None

    @property
    def asset_id(self) -> Optional[str]:
        value = self.api_dict.get(HbApi.ASSET_ID_FIELD)
        return value if isinstance(value, str) and value.strip() else None

    @property
    def sync_child_items_locations(self) -> Optional[bool]:
        value = self.api_dict.get(HbApi.SYNC_CHILD_ITEMS_LOCATIONS_FIELD)
        return value if isinstance(value, bool) else None

    @property
    def serial_number(self) -> str:
        return self.api_dict.get(HbApi.SERIAL_NUMBER_FIELD, '')

    @property
    def model_number(self) -> str:
        return self.api_dict.get(HbApi.MODEL_NUMBER_FIELD, '')

    @property
    def manufacturer(self) -> str:
        return self.api_dict.get(HbApi.MANUFACTURER_FIELD, '')

    @property
    def lifetime_warranty(self) -> Optional[bool]:
        value = self.api_dict.get(HbApi.LIFETIME_WARRANTY_FIELD)
        return value if isinstance(value, bool) else None

    @property
    def warranty_expires(self) -> Optional[str]:
        value = self.api_dict.get(HbApi.WARRANTY_EXPIRES_FIELD)
        return value if isinstance(value, str) and value.strip() else None

    @property
    def warranty_details(self) -> str:
        return self.api_dict.get(HbApi.WARRANTY_DETAILS_FIELD, '')

    @property
    def purchase_time(self) -> Optional[str]:
        value = self.api_dict.get(HbApi.PURCHASE_TIME_FIELD)
        return value if isinstance(value, str) and value.strip() else None

    @property
    def purchase_from(self) -> str:
        return self.api_dict.get(HbApi.PURCHASE_FROM_FIELD, '')

    @property
    def sold_time(self) -> Optional[str]:
        value = self.api_dict.get(HbApi.SOLD_TIME_FIELD)
        return value if isinstance(value, str) and value.strip() else None

    @property
    def sold_to(self) -> str:
        return self.api_dict.get(HbApi.SOLD_TO_FIELD, '')

    @property
    def sold_price(self) -> Optional[float]:
        value = self.api_dict.get(HbApi.SOLD_PRICE_FIELD)
        return value if isinstance(value, (int, float)) else None

    @property
    def sold_notes(self) -> str:
        return self.api_dict.get(HbApi.SOLD_NOTES_FIELD, '')

    @property
    def notes(self) -> str:
        return self.api_dict.get(HbApi.NOTES_FIELD, '')

    @property
    def location(self) -> Optional[Dict[str, Any]]:
        value = self.api_dict.get(HbApi.LOCATION_FIELD)
        return value if isinstance(value, dict) else None

    @property
    def labels(self) -> Optional[List[Dict[str, Any]]]:
        value = self.api_dict.get(HbApi.LABELS_FIELD)
        return value if isinstance(value, list) else None

    @property
    def attachments(self) -> List[Dict]:
        return self.api_dict.get(HbApi.ATTACHMENTS_FIELD, [])

    @property
    def fields(self) -> List[Dict]:
        return self.api_dict.get(HbApi.FIELDS_FIELD, [])

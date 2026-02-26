"""
Item
=======
Each Item will hold a single HomeBox Item.
It is basically a bunch of getters for each access to event data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from urllib.parse import quote

from .base import Base
from . import globals as g


class HbItem(Base):
    def __init__(self, api, item):
        self.api = api
        self._load(item)

    def _load(self, item):
        item_id = item.get('id')
        if not item_id:
            g.logger.Error('Item ID is required to initialize Item object')
            raise ValueError('Item ID is required to initialize Item object')

        url = f"{self.api.api_url}/v1/items/{item_id}"
        self.item = self.api._make_request(url=url, type='get')
    
    @property
    def id(self):
        """Returns item Id
        
        Returns:
            string: Item Id
        """
        return self.item['id']
    
    @property
    def name(self):
        """Returns item name
        
        Returns:
            string: item name
        """
        return self.item['name']
    
    @property
    def description(self):
        """Returns item description
        
        Returns:
            string: item description
        """
        return self.item['description']
    
    @property
    def quantity(self):
        """Returns item quantity
        
        Returns:
            int: item quantity
        """
        return self.item['quantity']
    
    @property
    def insured(self):
        """Returns if item is insured
        
        Returns:
            bool: insured or not
        """
        return bool(self.item['insured'])
    
    @property
    def archived(self):
        """Returns if item is archived
        
        Returns:
            bool: archived or not
        """
        return bool(self.item['archived'])
    
    @property
    def created_at(self):
        """Returns item creation datetime
        
        Returns:
            string: item creation datetime
        """
        return self.item['createdAt']
    
    @property
    def updated_at(self):
        """Returns item update datetime
        
        Returns:
            string: item update datetime
        """
        return self.item['updatedAt']
    
    @property
    def purchase_price(self):
        """Returns item purchase price
        
        Returns:
            float: purchase price
        """
        return self.item['purchasePrice']

    @property
    def location(self):
        """Returns item location
        
        Returns:
            dict: item location
        """
        return self.item['location']

    @property
    def labels(self):
        """Returns item labels
        
        Returns:
            list: item labels
        """
        return self.item['labels']

    @property
    def asset_id(self):
        """Returns item asset Id
        
        Returns:
            string: item asset Id
        """
        return self.item['assetId']

    @property
    def sync_child_items_locations(self):
        """Returns if child item locations should be synced
        
        Returns:
            bool: sync enabled or not
        """
        return bool(self.item['syncChildItemsLocations'])
    
    @property
    def serial_number(self):
        """Returns item serial number
        
        Returns:
            string: item serial number
        """
        return self.item['serialNumber']
    
    @property
    def model_number(self):
        """Returns item model number
        
        Returns:
            string: item model number
        """
        return self.item['modelNumber']
    
    @property
    def manufacturer(self):
        """Returns item manufacturer
        
        Returns:
            string: item manufacturer
        """
        return self.item['manufacturer']

    @property
    def lifetime_warranty(self):
        """Returns if item has lifetime warranty
        
        Returns:
            bool: lifetime warranty or not
        """
        return bool(self.item['lifetimeWarranty'])

    @property
    def warranty_expires(self):
        """Returns item warranty expiration datetime
        
        Returns:
            string: item warranty expiration datetime
        """
        return self.item['warrantyExpires']

    @property
    def warranty_details(self):
        """Returns item warranty details
        
        Returns:
            string: item warranty details
        """
        return self.item['warrantyDetails']

    @property
    def purchase_time(self):
        """Returns item purchase datetime
        
        Returns:
            string: item purchase datetime
        """
        return self.item['purchaseTime']

    @property
    def purchase_from(self):
        """Returns item purchase source
        
        Returns:
            string: item purchase source
        """
        return self.item['purchaseFrom']

    @property
    def sold_time(self):
        """Returns item sold datetime
        
        Returns:
            string: item sold datetime
        """
        return self.item['soldTime']
    
    @property
    def sold_to(self):
        """Returns item sold target
        
        Returns:
            string: item sold target
        """
        return self.item['soldTo']
    
    @property
    def sold_price(self):
        """Returns item sold price
        
        Returns:
            float: item sold price
        """
        return self.item['soldPrice']

    @property
    def sold_notes(self):
        """Returns item sold notes
        
        Returns:
            string: item sold notes
        """
        return self.item['soldNotes']

    @property
    def notes(self):
        """Returns item notes
        
        Returns:
            string: item notes
        """
        return self.item['notes']

    @property
    def attachments(self):
        """Returns item attachments
        
        Returns:
            list: item attachments
        """
        return self.item['attachments']

    def download_attachment(self, attachment=None):
        if not isinstance(attachment, dict):
            g.logger.Error(f'Invalid attachment provided for download: expected dict, got {type(attachment)}')
            return None
        
        attachment_id = str(attachment.get('id', '')).strip()

        if not attachment_id:
            g.logger.Debug(1, f'Cannot download attachment for item {self.id}: missing attachment id')
            return None

        content_type_hint = str(attachment.get('mimeType', '')).strip()
        filename_hint = str(attachment.get('title', '')).strip()
        url = f"{self.api.api_url}/v1/items/{self.id}/attachments/{attachment_id}"

        response = self.api._make_request(url=url, return_raw_response=True)

        if not response.content:
            g.logger.Debug(2, f'Attachment download returned empty payload: {url}')
            return None

        content_type = response.headers.get('content-type', '') or content_type_hint

        return {
            'content': response.content,
            'mime_type': content_type,
            'filename': filename_hint,
            'source_url': url,
        }
    
    @property
    def fields(self):
        """Returns item custom fields
        
        Returns:
            list: item custom fields
        """
        return self.item['fields']
    
    def get(self):
        """Returns item object
        
        Returns:
            :class:`hb_client.helpers.Item`: Item object
        """
        return self.item

    def update(self, options={}):
        """Partially updates an existing item (PATCH).
        Args:
            options (dict): Set of attributes that define the item:
                {
                    'locationId': string
                    'quantity'  : string
                    'tagIds'    : string
                }
        Returns:
            json: json response of API request
        """

        url = f"{self.api.api_url}/v1/items/{self.id}"

        return self.api._make_request(url=url, payload=options, type='patch')
    
    def replace(self, options={}):
        """
        Fully updates an existing item (PUT).

        Args:
            options (dict): Complete representation of the item. Must include all required fields for full replacement.

                Expected structure::

                    {
                        "name": str,
                        "archived": bool,
                        "assetId": str,
                        "description": str,
                        "insured": bool,
                        "lifetimeWarranty": bool,
                        "locationId": str,
                        "manufacturer": str,
                        "modelNumber": str,
                        "notes": str,
                        "parentId": str,
                        "purchaseFrom": str,
                        "purchasePrice": float,
                        "purchaseTime": str,
                        "quantity": int,
                        "serialNumber": str,
                        "soldNotes": str,
                        "soldPrice": float,
                        "soldTime": str,
                        "soldTo": str,
                        "syncChildItemsLocations": bool,
                        "tagIds": List[str],
                        "warrantyDetails": str,
                        "warrantyExpires": str,
                        "fields": List[dict]  # Custom fields:
                            [
                                {
                                    "id": str,
                                    "name": str,
                                    "type": str,
                                    "booleanValue": bool,
                                    "numberValue": int,
                                    "textValue": str
                                }
                            ]
                    }
        Returns:
            dict: JSON response returned by the API.
        """

        url = f"{self.api.api_url}/v1/items/{self.id}"

        return self.api._make_request(url=url, payload=options, type='put')

    def duplicate(self, options={}):
        """
        Duplicates an existing item.

        Args:
            options (dict): Options for duplication. Must include the following fields:

                Expected structure:
                    {
                        "copyAttachments": bool,
                        "copyCustomFields": bool,
                        "copyMaintenance": bool,
                        "copyPrefix": str,
                    }
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/v1/items/{self.id}/duplicate"

        return self.api._make_request(url=url, payload=options, type='post')

    def delete(self):
        """Deletes item
        
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/items/{self.id}"

        return self.api._make_request(url=url, type='delete')

    def maintenances(self, options={}):
        """Get all maintenances for an item.

        Args:
            options (dict): Maintenance log details. Must include the following fields:

                Expected structure:
                    {
                        "status": str, #Allowed values: scheduled, completed, both
                    }
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/v1/items/{self.id}/maintenance"

        return self.api._make_request(url=url, query=options, type='get')
    
    def add_maintenance_entry(self, options={}):
        """
        Adds a maintenance entry for an item.
        Args:
            options (dict): Maintenance log entry details. Must include the following fields:
                {
                    "completedDate": str,
                    "cost": str,
                    "description": str,
                    "name": str,
                    "scheduledDate": str
                }
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/v1/items/{self.id}/maintenance"

        return self.api._make_request(url=url, payload=options, type='post')
    
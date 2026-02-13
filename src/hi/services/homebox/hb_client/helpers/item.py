"""
Item
=======
Each Item will hold a single HomeBox Item.
It is basically a bunch of getters for each access to event data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .base import Base


class Item(Base):
    def __init__(self, api=None, item=None):
        self.api = api
        self.item = item
    
    def get(self):
        """Returns item object
        
        Returns:
            :class:`hb_client.helpers.Item`: Item object
        """
        return self.item
    
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
    def purchase_price(self):
        """Returns item purchase price
        
        Returns:
            float: purchase price
        """
        return self.item['purchasePrice']
    
    def get_full_item(self):
        """Returns full item object
    
        Returns:
            json: json response of API request
        """

        url = f"{self.api.api_url}/v1/items/{self.id}"

        return self.api._make_request(url=url, type='get')

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

        return self.api._make_request(url=url, data=options, type='patch')
    
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

        return self.api._make_request(url=url, data=options, type='put')

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

        return self.api._make_request(url=url, data=options, type='post')

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

        return self.api._make_request(url=url, data=options, type='post')
    
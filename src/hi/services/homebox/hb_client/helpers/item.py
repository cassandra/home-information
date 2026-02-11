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
    
    def update(self, options={}):
        """Partially updates an existing item
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

        return self.api._make_request(url=url, type='patch')
    
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

        return self.api._make_request(url=url, type='put')

    def delete(self):
        """Deletes item
        
        Returns:
            json: API response
        """
        url = f"{self.api.api_url}/items/{self.id}"

        return self.api._make_request(url=url, type='delete')

    def set_parameter(self, options={}):
        """Changes item parameters
        
        Args:
            options (dict, optional): As below. Defaults to {}::

                {
                    'function': string # function of item
                    'name': string # name of item
                    'enabled': boolean
                    'raw': {
                        # Any other item value that is not exposed above. Example:
                        'Item[Colours]': '4',
                        'Item[Method]': 'simple'
                    }

                }
    
        
        Returns:
            json: API Response
        """
        url = self.api.api_url + '/monitors/{}.json'.format(self.id())
        payload = {}
        if options.get('function'):
            payload['Monitor[Function]'] = options.get('function')
        if options.get('name'):
            payload['Monitor[Name]'] = options.get('name')
        if options.get('enabled') is not None:
            enabled = '1' if options.get('enabled') else '0'
            payload['Monitor[Enabled]'] = enabled

        if options.get('raw'):
            for k in options.get('raw'):
                payload[k] = options.get('raw')[k]
               
        if payload:
            return self.api._make_request(url=url, payload=payload, type='post')

    def status(self):
        """Returns status of monitor, as reported by zmdc
            TBD: crappy return, need to normalize
        
        Returns:
            json: API response
        """
        url = self.api.api_url + '/monitors/daemonStatus/id:{}/daemon:zmc.json'.format(self.id())
        return self.api._make_request(url=url)

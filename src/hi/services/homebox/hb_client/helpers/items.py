"""
Items
=========
Holds a list of Items for a HB configuration
"""


from .base import Base
from .item import Item
from . import globals as g


class Items(Base):
    def __init__(self, api=None):
        self.api = api
        self._load()

    def _load(self, options={}):
        g.logger.Debug(2, 'Retrieving items via API')

        url = self.api.api_url + 'v1/items'
        r = self.api._make_request(url=url)
        items = r.get('items')

        self.items = []
        for i in items:
            self.items.append(Item(api=self.api, item=i))

    def list(self):
        return self.items

    def add(self, options={}):
        """Adds a new item
        Args:
            options (dict): Set of attributes that define the item:
                {
                    'description': string
                    'locationId' : string
                    'name'       : string
                    'parentId'   : string
                    'quantity'   : integer
                    'tagIds'     : Array<string>
                }
        Returns:
            json: json response of API request
        """

        if not options.get('name'):
            g.logger.Error('Name is required to add item')
            return

        url = f"{self.api.api_url}/v1/items"

        return self.api._make_request(url=url, payload=options, type="post")

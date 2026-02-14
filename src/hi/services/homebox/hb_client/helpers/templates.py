"""
Items
=========
Holds a list of Items for a HB configuration
"""


from .base import Base
from .template import Template
from . import globals as g


class Templates(Base):
    def __init__(self, api=None):
        self.api = api
        self._load()

    def _load(self, options={}):
        g.logger.Debug(2, 'Retrieving item templates via API')

        url = f"{self.api.api_url}/v1/templates"
        templates = self.api._make_request(url=url)

        self.templates = []
        for t in templates:
            self.templates.append(Template(api=self.api, template=t))

    def list(self):
        return self.templates

    def add(self, options={}):
        """Adds a new item template
        Args:
            options (dict): Set of attributes that define the item template:
                {
                    "defaultDescription": str,
                    "defaultInsured" : bool,
                    "defaultLifetimeWarranty": bool,
                    "defaultLocationId": str,
                    "defaultManufacturer": str,
                    "defaultModelNumber": str,
                    "defaultName": str,
                    "defaultQuantity": int,
                    "defaultTagIds": List[str],
                    "defaultWarrantyDetails": str,
                    "description": str,
                    "includePurchaseFields": bool,
                    "includeSoldFields": bool,
                    "includeWarrantyFields": bool,
                    "name": str,
                    "notes": str,
                    "fields": List[dict] # Custom fields:
                        [
                            {
                                "id": str,
                                "name": str,
                                "textValue": str,
                                "type": str
                            }
                        ]
                }
        Returns:
            json: json response of API request
        """

        if not options.get('name'):
            g.logger.Error('Name is required to add item template')
            return

        url = f"{self.api.api_url}/v1/templates"

        return self.api._make_request(url=url, payload=options, type="post")

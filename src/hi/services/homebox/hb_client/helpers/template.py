"""
Item Template
=======
Each Item Template will hold a single HomeBox Item Template.
It is basically a bunch of getters for each access to event data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .base import Base
from . import globals as g


class Template(Base):
    def __init__(self, api, template):
        self.api = api
        self._load(template)

    def _load(self, template):
        template_id = template.get('id')
        if not template_id:
            g.logger.Error('Template ID is required to initialize Template object')
            return

        url = f"{self.api.api_url}/v1/templates/{template_id}"
        self.template = self.api._make_request(url=url, type='get')
    
    @property
    def id(self):
        """Returns item template Id
        
        Returns:
            string: Item template Id
        """
        return self.template['id']
    
    @property
    def name(self):
        """Returns item template name
        
        Returns:
            string: item template name
        """
        return self.template['name']
    
    @property
    def description(self):
        """Returns item template description
        
        Returns:
            string: item template description
        """
        return self.template['description']

    @property
    def notes(self):
        """Returns item template notes
        
        Returns:
            string: item template notes
        """
        return self.template['notes']

    @property
    def created_at(self):
        """Returns item template creation datetime
        
        Returns:
            string: item template creation datetime
        """
        return self.template['createdAt']

    @property
    def updated_at(self):
        """Returns item template update datetime
        
        Returns:
            string: item template update datetime
        """
        return self.template['updatedAt']

    @property
    def default_quantity(self):
        """Returns item template default quantity
        
        Returns:
            int: item template default quantity
        """
        return self.template['defaultQuantity']

    @property
    def default_insured(self):
        """Returns if default item is insured
        
        Returns:
            bool: insured or not
        """
        return bool(self.template['defaultInsured'])

    @property
    def default_name(self):
        """Returns item template default item name
        
        Returns:
            string: item template default item name
        """
        return self.template['defaultName']

    @property
    def default_description(self):
        """Returns item template default item description
        
        Returns:
            string: item template default item description
        """
        return self.template['defaultDescription']

    @property
    def default_manufacturer(self):
        """Returns item template default manufacturer
        
        Returns:
            string: item template default manufacturer
        """
        return self.template['defaultManufacturer']

    @property
    def default_model_number(self):
        """Returns item template default model number
        
        Returns:
            string: item template default model number
        """
        return self.template['defaultModelNumber']

    @property
    def default_lifetime_warranty(self):
        """Returns if default item has lifetime warranty
        
        Returns:
            bool: lifetime warranty or not
        """
        return bool(self.template['defaultLifetimeWarranty'])

    @property
    def default_warranty_details(self):
        """Returns item template default warranty details
        
        Returns:
            string: item template default warranty details
        """
        return self.template['defaultWarrantyDetails']

    @property
    def default_location(self):
        """Returns item template default location
        
        Returns:
            dict: item template default location
        """
        return self.template['defaultLocation']

    @property
    def default_labels(self):
        """Returns item template default labels
        
        Returns:
            list: item template default labels
        """
        return self.template['defaultLabels']

    @property
    def include_warranty_fields(self):
        """Returns if warranty fields are included by default
        
        Returns:
            bool: included or not
        """
        return bool(self.template['includeWarrantyFields'])

    @property
    def include_purchase_fields(self):
        """Returns if purchase fields are included by default
        
        Returns:
            bool: included or not
        """
        return bool(self.template['includePurchaseFields'])

    @property
    def include_sold_fields(self):
        """Returns if sold fields are included by default
        
        Returns:
            bool: included or not
        """
        return bool(self.template['includeSoldFields'])

    @property
    def fields(self):
        """Returns item template custom fields
        
        Returns:
            list: item template custom fields
        """
        return self.template['fields']
    
    def get(self):
        """Returns item template object
        
        Returns:
            :class:`hb_client.helpers.template.Template`: Template object
        """
        return self.template
    
    def update(self, options={}):
        """
        Updates an existing item template.

        Args:
            options (dict): Template Data.

                Expected structure::

                    {
                        "name": str,
                        "description": str,
                        "notes": str,
                        "defaultQuantity": int,
                        "defaultInsured": bool,
                        "defaultName": str,
                        "defaultDescription": str,
                        "defaultManufacturer": str,
                        "defaultModelNumber": str,
                        "defaultLifetimeWarranty": bool,
                        "defaultWarrantyDetails": str,
                        "defaultLocationId": str,
                        "defaultLabelIds": List[str],
                        "includeWarrantyFields": bool,
                        "includePurchaseFields": bool,
                        "includeSoldFields": bool,
                        "fields": List[dict]  # Custom fields:
                            [
                                {
                                    "id": str,
                                    "name": str,
                                    "type": str,
                                    "textValue": str
                                }
                            ]
                    }
        Returns:
            dict: JSON response returned by the API.
        """

        url = f"{self.api.api_url}/v1/templates/{self.id}"

        return self.api._make_request(url=url, payload=options, type='put')

    def delete(self):
        """Deletes item template
        
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/v1/templates/{self.id}"

        return self.api._make_request(url=url, type='delete')

    def create_item_from_template(self, options={}):
        """
        Creates an item from this template.

        Args:
            options (dict): Item Data.

                Expected structure::

                    {
                        "description": str,
                        "locationId": str,
                        "name": str,
                        "quantity": int,
                        "labelIds": List[str],
                    }

        Returns:
            dict: JSON response returned by the API.
        """

        url = f"{self.api.api_url}/v1/templates/{self.id}/create-item"

        return self.api._make_request(url=url, payload=options, type='post')
    
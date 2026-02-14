"""
Maintenance
========
Each Maintenance will hold a single HomeBox Maintenance.
It is basically a bunch of getters for each access to maintenance data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .base import Base


class Maintenance(Base):
    def __init__(self, api=None, maintenance=None):
        self.api = api
        self.maintenance = maintenance
    
    @property
    def id(self):
        """Returns maintenance Id
        
        Returns:
            string: Maintenance Id
        """
        return self.maintenance['id']
    
    @property
    def completed_date(self):
        """Returns completed date of maintenance
        
        Returns:
            string: completed date of maintenance
        """
        return self.maintenance['completedDate']

    @property
    def scheduled_date(self):
        """Returns scheduled date of maintenance
        
        Returns:
            string: scheduled date of maintenance
        """
        return self.maintenance['scheduledDate']

    @property
    def name(self):
        """Returns maintenance name
        
        Returns:
            string: maintenance name
        """
        return self.maintenance['name']
    
    @property
    def description(self):
        """Returns maintenance description
        
        Returns:
            string: maintenance description
        """
        return self.maintenance['description']
    
    @property
    def cost(self):
        """Returns maintenance cost
        
        Returns:
            string: maintenance cost
        """
        return self.maintenance['cost']
    
    @property
    def item_name(self):
        """Returns maintenance item name
        
        Returns:
            string: maintenance item name
        """
        return self.maintenance['itemName']
    
    @property
    def item_id(self):
        """Returns maintenance item Id
        
        Returns:
            string: maintenance item Id
        """
        return self.maintenance['itemId']

    def get(self):
        """Returns maintenance object
        
        Returns:
            :class:`hb_client.helpers.maintenance.Maintenance`: Maintenance object
        """
        return self.maintenance

    def update(self, options={}):
        """
        Updates an existing maintenance.

        Args:
            options (dict): Complete representation of the maintenance.

                Expected structure::
                    {
                        "completedDate": str,
                        "cost": bool,
                        "description": str,
                        "name": str
                        "scheduledDate": str
                    }
        Returns:
            dict: JSON response returned by the API.
        """

        url = f"{self.api.api_url}/v1/maintenance/{self.id}"

        return self.api._make_request(url=url, data=options, type='put')

    def delete(self):
        """Deletes maintenance
        
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/v1/maintenance/{self.id}"

        return self.api._make_request(url=url, type='delete')

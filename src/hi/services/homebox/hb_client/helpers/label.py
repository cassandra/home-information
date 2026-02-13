"""
Location
========
Each Location will hold a single HomeBox Location.
It is basically a bunch of getters for each access to location data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .base import Base


class Label(Base):
    def __init__(self, api=None, label=None):
        self.api = api
        self.label = label
    
    @property
    def id(self):
        """Returns label Id
        
        Returns:
            string: Label Id
        """
        return self.label['id']
    
    @property
    def name(self):
        """Returns label name
        
        Returns:
            string: label name
        """
        return self.label['name']
    
    @property
    def description(self):
        """Returns label description
        
        Returns:
            string: label description
        """
        return self.label['description']
    
    @property
    def color(self):
        """Returns label color
        
        Returns:
            string: label color
        """
        return self.label['color']
    
    @property
    def created_at(self):
        """Returns label creation date
        
        Returns:
            string: label creation date
        """
        return self.label['createdAt']
    
    @property
    def updated_at(self):
        """Returns label update date
        
        Returns:
            string: label update date
        """
        return self.label['updatedAt']
    
    def get(self):
        """Returns label object
        
        Returns:
            :class:`hb_client.helpers.label.Label`: Label object
        """
        return self.label

    def update(self, options={}):
        """
        Updates an existing label.

        Args:
            options (dict): Complete representation of the label.

                Expected structure::
                    {
                        "name": str,
                        "description": str,
                        "color": str
                    }
        Returns:
            dict: JSON response returned by the API.
        """

        url = f"{self.api.api_url}/v1/labels/{self.id}"

        return self.api._make_request(url=url, payload=options, type='put')

    def delete(self):
        """Deletes label
        
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/v1/labels/{self.id}"

        return self.api._make_request(url=url, type='delete')

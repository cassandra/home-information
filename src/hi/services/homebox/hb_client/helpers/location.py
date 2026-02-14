"""
Location
========
Each Location will hold a single HomeBox Location.
It is basically a bunch of getters for each access to location data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .base import Base


class Location(Base):
    def __init__(self, api, location):
        self.api = api
        self._load(location)

    def _load(self, location):
        location_id = location.get('id')
        if not location_id:
            raise ValueError('Location ID is required to initialize Location object')

        url = f"{self.api.api_url}/v1/locations/{location_id}"
        self.location = self.api._make_request(url=url, type='get')
    
    @property
    def id(self):
        """Returns location Id
        
        Returns:
            string: Location Id
        """
        return self.location['id']
    
    @property
    def name(self):
        """Returns location name
        
        Returns:
            string: location name
        """
        return self.location['name']
    
    @property
    def description(self):
        """Returns location description
        
        Returns:
            string: location description
        """
        return self.location['description']
    
    @property
    def created_at(self):
        """Returns location creation date
        
        Returns:
            string: location creation date
        """
        return self.location['createdAt']
    
    @property
    def updated_at(self):
        """Returns location update date
        
        Returns:
            string: location update date
        """
        return self.location['updatedAt']   
    
    @property
    def children(self):
        """Returns location children
        
        Returns:
            list: list of location children
        """
        return self.location['children']

    def get(self):
        """Returns location object
        
        Returns:
            :class:`hb_client.helpers.location.Location`: Location object
        """
        return self.location

    def update(self, options={}):
        """
        Updates an existing location.

        Args:
            options (dict): Complete representation of the location.

                Expected structure::
                    {
                        "description": str,
                        "id": bool,
                        "name": str,
                        "parentId": str
                    }
        Returns:
            dict: JSON response returned by the API.
        """

        url = f"{self.api.api_url}/v1/locations/{self.id}"

        return self.api._make_request(url=url, data=options, type='put')

    def delete(self):
        """Deletes location
        
        Returns:
            json: API response
        """

        url = f"{self.api.api_url}/locations/{self.id}"

        return self.api._make_request(url=url, type='delete')

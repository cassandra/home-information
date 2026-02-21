"""
Locations
=========
Holds a list of Locations for a HB configuration
"""


from .base import Base
from .location import Location
from . import globals as g


class Locations(Base):
    def __init__(self, api=None):
        self.api = api
        self._load()

    def _load(self, options={}):
        g.logger.Debug(2, 'Retrieving locations via API')

        url = f"{self.api.api_url}/v1/locations"
        locations = self.api._make_request(url=url)

        self.locations = []
        for loc in locations:
            self.locations.append(Location(api=self.api, location=loc))

    def list(self):
        return self.locations

    def add(self, options={}):
        """Adds a new location
        Args:
            options (dict): Set of attributes that define the location:
                {
                    "description": str,
                    "name": str,
                    "parentId": str
                }
        Returns:
            json: json response of API request
        """

        if not options.get('name'):
            g.logger.Error('Name is required to add item')
            return

        url = f"{self.api.api_url}/v1/locations"

        return self.api._make_request(url=url, payload=options, type="post")

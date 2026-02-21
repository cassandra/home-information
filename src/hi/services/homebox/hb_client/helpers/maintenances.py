"""
Maintenances
=========
Holds a list of Maintenances for a HB configuration
"""


from .base import Base
from .maintenance import Maintenance
from . import globals as g


class Maintenances(Base):
    def __init__(self, api=None):
        self.api = api
        self._load(options={"status": "both"})

    def _load(self, options={}):
        """Load maintenances from the API.
        Args:
            options (dict): Supported options for this method. Only one key is
                supported:
                {
                    "status": str
                }
                The `status` key is required and must be one of:
                - "scheduled"
                - "completed"
                - "both"
                Default: "both".
        """
        g.logger.Debug(2, 'Retrieving maintenances via API')

        url = f"{self.api.api_url}/v1/maintenance"
        maintenances = self.api._make_request(url=url, query=options)

        self.maintenances = []
        for m in maintenances:
            self.maintenances.append(Maintenance(api=self.api, maintenance=m))

    def list(self):
        return self.maintenances

    def add(self, options={}):
        """Adds a new maintenance
        Args:
            options (dict): Set of attributes that define the maintenance:
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

        url = f"{self.api.api_url}/v1/maintenances"

        return self.api._make_request(url=url, payload=options, type="post")

"""
Notifiers
=========
Holds a list of Notifiers for a HB configuration
"""


from .base import Base
from .notifier import Notifier
from . import globals as g


class Notifiers(Base):
    def __init__(self, api=None):
        self.api = api
        self._load()

    def _load(self, options={}):
        g.logger.Debug(2, 'Retrieving notifiers via API')

        url = f"{self.api.api_url}/v1/notifiers"
        notifiers = self.api._make_request(url=url)

        self.notifiers = []
        for n in notifiers:
            self.notifiers.append(Notifier(api=self.api, notifier=n))

    def list(self):
        return self.notifiers

    def add(self, options={}):
        """Adds a new notifier
        Args:
            options (dict): Set of attributes that define the notifier:
                {
                    "isActive": bool,
                    "name": str,
                    "url": str,
                }
        Returns:
            json: json response of API request
        """

        url = f"{self.api.api_url}/v1/notifiers"

        return self.api._make_request(url=url, payload=options, type="post")
